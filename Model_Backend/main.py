"""
main.py — FastAPI server for the Customs X-ray Intelligence Platform.

Bridges the React frontend to the existing Python ML utilities:
  - XRayDetector              (YOLOv8 object detection)
  - generate_gradcam          (pseudo Grad-CAM heatmap)
  - calculate_risk            (legacy CLEAR/SUSPICIOUS/PROHIBITED scoring)
  - ZeroShotManifestInspector (OWL-ViT v2 + SAM 2)
  - draw_inspection_overlay   (annotated zero-shot image)
  - compute_visual_risk       (Stage 6 composite visual risk)
  - compute_final_risk        (Stage 7–8 final risk + RED/YELLOW/GREEN)

Endpoints:
  POST /api/analyze           — run full pipeline on an uploaded X-ray scan
  POST /api/manifest/extract  — extract item list from a manifest PDF
  GET  /api/files?path=...    — serve generated output files
  GET  /api/health            — health check
"""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Load .env before anything else reads env vars
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, rely on system env vars

import cv2
import numpy as np
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image

# ── Internal utilities ──────────────────────────────────────────────────
from utils.audit import AuditTrail
from utils.detector import XRayDetector
from utils.ipfs_client import upload_to_ipfs, fetch_from_ipfs
from utils.supabase_client import store_audit_metadata, query_audits
from utils.encryption import encrypt_data, decrypt_data
from utils.gradcam import generate_gradcam, overlay_heatmap
from utils.image_comparator import compare_scans
from utils.risk_scorer import calculate_risk
from utils.zero_shot_inspector import (
    DEFAULT_SCAN_LABELS,
    ZeroShotManifestInspector,
    draw_inspection_overlay,
)
from utils.visual_risk import compute_visual_risk, ssim_score_to_risk
from utils.final_risk import compute_final_risk

# ── SHAP explainer — optional, degrades gracefully ─────────────────────
# shap_explainer.py contains module-level Colab execution code (files.upload,
# hardcoded Colab paths) that raises NameError / FileNotFoundError outside
# Google Colab.  We catch any import-time exception so the rest of the
# pipeline continues; shap_intensity_score will be None in that case.
try:
    from utils.shap_explainer import YOLOShapExplainer
    SHAP_AVAILABLE = True
except Exception as _shap_import_err:
    YOLOShapExplainer = None  # type: ignore[assignment, misc]
    SHAP_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "YOLOShapExplainer unavailable — shap_intensity_score will be None. "
        "Reason: %s", _shap_import_err,
    )

# ── Configuration ───────────────────────────────────────────────────────

MODEL_PATH = os.environ.get("MODEL_PATH", "model/best.pt")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "outputs")).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Whether to load the heavy zero-shot inspector at startup.
# Set ENABLE_ZERO_SHOT=1 to enable (requires OWL-ViT + SAM 2 weights).
ENABLE_ZERO_SHOT = os.environ.get("ENABLE_ZERO_SHOT", "1") == "1"

# Prohibited / suspicious label sets (shared with frontend constants.js)
PROHIBITED_LABELS = {"gun", "bullet", "knife"}
SUSPICIOUS_LABELS = {
    "baton", "plier", "hammer", "powerbank", "scissors",
    "wrench", "sprayer", "handcuffs", "lighter",
}
_ALL_THREAT_LABELS = PROHIBITED_LABELS | SUSPICIOUS_LABELS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── App ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Pixel — Customs X-ray Intelligence API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Model loading (lazy singletons) ────────────────────────────────────

_detector: Optional[XRayDetector] = None
_zero_shot: Optional[ZeroShotManifestInspector] = None


def get_detector() -> XRayDetector:
    """Lazy-load the YOLOv8 detector on first use."""
    global _detector
    if _detector is None:
        if not Path(MODEL_PATH).exists():
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Model weights not found at '{MODEL_PATH}'. "
                    "Place your YOLOv8 best.pt in Model_Backend/model/best.pt "
                    "or set the MODEL_PATH environment variable."
                ),
            )
        logger.info("Loading XRayDetector from %s …", MODEL_PATH)
        _detector = XRayDetector(model_path=MODEL_PATH)
        logger.info("✓ XRayDetector ready")
    return _detector


def get_zero_shot() -> Optional[ZeroShotManifestInspector]:
    """Lazy-load the zero-shot inspector (if enabled)."""
    global _zero_shot
    if not ENABLE_ZERO_SHOT:
        return None
    if _zero_shot is None:
        logger.info("Loading ZeroShotManifestInspector …")
        _zero_shot = ZeroShotManifestInspector()
        logger.info("✓ ZeroShotManifestInspector ready")
    return _zero_shot


# ── Helpers ─────────────────────────────────────────────────────────────


def _save_upload_to_temp(upload: UploadFile, suffix: str = "") -> Path:
    """Save an UploadFile to a temp file and return its path."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    shutil.copyfileobj(upload.file, tmp)
    tmp.close()
    return Path(tmp.name)


def _categorize_label(label: str) -> str:
    """Map a detection label to prohibited / suspicious / clear."""
    normalized = label.strip().lower()
    if normalized in PROHIBITED_LABELS:
        return "prohibited"
    if normalized in SUSPICIOUS_LABELS:
        return "suspicious"
    return "clear"


def _xyxy_to_xywh(bbox: list[float]) -> dict:
    """Convert [x1, y1, x2, y2] → {x, y, width, height}."""
    x1, y1, x2, y2 = bbox
    return {
        "x": round(x1, 2),
        "y": round(y1, 2),
        "width": round(x2 - x1, 2),
        "height": round(y2 - y1, 2),
    }


def _transform_detections(
    raw_detections: list[dict],
) -> list[dict]:
    """
    Enrich raw detector output to match the frontend contract:
      - Add sequential `id`
      - Add `category` (prohibited / suspicious / clear)
      - Convert bbox from [x1,y1,x2,y2] to {x,y,width,height}
    """
    result = []
    for idx, det in enumerate(raw_detections, start=1):
        result.append({
            "id": idx,
            "label": det["label"],
            "confidence": round(det["confidence"], 4),
            "category": _categorize_label(det["label"]),
            "bbox": _xyxy_to_xywh(det["bbox"]),
        })
    return result


def _unique_output_path(name: str, ext: str = ".png") -> Path:
    """Generate a unique file path under OUTPUT_DIR."""
    stamp = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    filename = f"{name}_{stamp}{ext}"
    return OUTPUT_DIR / filename


def _run_ssim_sync(tmp_ref_path: str, image: Image.Image):
    """
    Open the reference image and compute SSIM comparison.
    Runs in a thread pool via asyncio.to_thread() — must not call
    async functions or use async context managers.
    Returns a ComparisonResult or raises on failure.
    """
    ref_image = Image.open(tmp_ref_path).convert("RGB")
    return compare_scans(image, ref_image)


def _extract_shap_intensity(
    detector: XRayDetector,
    image: Image.Image,
) -> Optional[float]:
    """
    Run the SHAP explainer and return a normalised intensity score in [0, 1].

    Derivation: conclusion["high_attribution_coverage_pct"] / 100.0
    (high_attribution_coverage_pct is the fraction of pixels above the SHAP
    threshold, expressed as %; dividing by 100 gives a [0, 1] risk proxy.)

    Returns None when:
      - SHAP is unavailable (module failed to import)
      - No detection was found in the image
      - Any exception occurs during SHAP computation

    Runs in a thread pool via asyncio.to_thread().
    """
    if not SHAP_AVAILABLE or YOLOShapExplainer is None:
        return None
    try:
        explainer = YOLOShapExplainer(
            detector,
            suspicious_labels=_ALL_THREAT_LABELS,
        )
        result = explainer.explain(image, max_evals=100)
        if result is None:
            return None
        _, _, _, conclusion = result
        return min(conclusion["high_attribution_coverage_pct"] / 100.0, 1.0)
    except Exception as exc:
        logger.warning("SHAP explanation failed: %s", exc)
        return None


# ── Endpoint: POST /api/analyze ────────────────────────────────────────


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    reference: Optional[UploadFile] = File(None),
    manifest: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = None,
):
    """
    Run the full analysis pipeline on an uploaded X-ray scan image.

    Pipeline:
      Stage 1  : YOLO detection + SSIM comparison (parallel via asyncio.gather)
      Stage 2  : Legacy risk scoring (CLEAR / SUSPICIOUS / PROHIBITED)
      Stage 3  : Grad-CAM heatmap
      Stage 3b : SSIM result processing (save heatmap images)
      Stage 3c : SHAP intensity score
      Stage 4  : Zero-shot inspection
      Stage 5–8: Composite risk (visual_risk → final_risk → RED/YELLOW/GREEN)

    Returns {detections, risk, outputs, suspicious_flag, request_id}
    matching the full frontend contract.
    """
    # --- Validate ---
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="'file' must be an image")

    tmp_path: Optional[Path] = None
    tmp_ref_path: Optional[Path] = None
    tmp_manifest_path: Optional[Path] = None

    try:
        # ── Audit: create a fresh trail for this request ────────────
        audit = AuditTrail()

        # --- Save uploads ---
        suffix = Path(file.filename or "scan.png").suffix or ".png"
        tmp_path = _save_upload_to_temp(file, suffix=suffix)
        image = Image.open(str(tmp_path)).convert("RGB")

        if reference is not None:
            ref_suffix = Path(reference.filename or "ref.png").suffix or ".png"
            tmp_ref_path = _save_upload_to_temp(reference, suffix=ref_suffix)

        # Extract manifest items if a manifest PDF was included
        manifest_items: list[str] = []
        if manifest is not None:
            tmp_manifest_path = _save_upload_to_temp(manifest, suffix=".pdf")
            t0 = time.time()
            manifest_items = _extract_items_from_pdf(tmp_manifest_path)
            audit.log_step(
                service="manifest_extraction",
                status="success",
                input_data={"filename": manifest.filename},
                output_data={"item_count": len(manifest_items), "items": manifest_items},
                latency=time.time() - t0,
            )

        # ── Stage 1: YOLO detection + SSIM comparison (parallel) ────
        #
        # Both are CPU-bound and independent — run them concurrently in the
        # default thread pool so they don't block each other on the GIL
        # (YOLO/PyTorch releases the GIL during inference; OpenCV operations
        # inside SSIM also release the GIL for most calls).
        detector = get_detector()
        parallel_t0 = time.time()

        if tmp_ref_path is not None:
            yolo_task = asyncio.to_thread(detector.detect, image)
            ssim_task = asyncio.to_thread(_run_ssim_sync, str(tmp_ref_path), image)

            yolo_outcome, ssim_outcome = await asyncio.gather(
                yolo_task, ssim_task, return_exceptions=True
            )

            # YOLO failure is fatal for the whole request
            if isinstance(yolo_outcome, Exception):
                raise yolo_outcome

            raw_detections: list[dict] = yolo_outcome

            # SSIM failure is non-fatal — log and continue without comparison
            if isinstance(ssim_outcome, Exception):
                logger.warning("SSIM parallel task failed: %s", ssim_outcome)
                audit.log_step(
                    service="ssim_comparison",
                    status="failed",
                    error=str(ssim_outcome),
                )
                ssim_result = None
            else:
                ssim_result = ssim_outcome
        else:
            raw_detections = await asyncio.to_thread(detector.detect, image)
            ssim_result = None

        parallel_wall = time.time() - parallel_t0
        detections = _transform_detections(raw_detections)

        audit.log_step(
            service="yolov8_detection",
            status="success",
            input_data={"filename": file.filename, "image_size": list(image.size)},
            output_data={
                "detection_count": len(detections),
                "labels": [d["label"] for d in detections],
            },
            latency=parallel_wall,
            model_version=MODEL_PATH,
        )

        # ── Stage 2: Legacy risk scoring (CLEAR / SUSPICIOUS / PROHIBITED) ──
        t0 = time.time()
        risk = calculate_risk(raw_detections)
        audit.log_step(
            service="risk_scoring",
            status="success",
            input_data={"detection_count": len(raw_detections)},
            output_data={"level": risk.get("level"), "score": risk.get("score")},
            latency=time.time() - t0,
        )

        # ── Stage 3: Grad-CAM heatmap ────────────────────────────────
        outputs: dict = {}
        try:
            t0 = time.time()
            gradcam_image = await asyncio.to_thread(generate_gradcam, MODEL_PATH, image)
            gradcam_path = _unique_output_path("gradcam")
            gradcam_image.save(str(gradcam_path))
            outputs["gradcam"] = str(gradcam_path.relative_to(OUTPUT_DIR.parent))
            audit.log_step(
                service="gradcam_generation",
                status="success",
                input_data={"image_size": list(image.size)},
                output_data={"output_path": outputs["gradcam"]},
                latency=time.time() - t0,
            )
        except Exception as exc:
            logger.warning("Grad-CAM generation failed: %s", exc)
            audit.log_step(
                service="gradcam_generation",
                status="failed",
                error=str(exc),
            )

        # ── Stage 3b: Process SSIM result (computed in parallel above) ──
        #
        # Computation already happened; this stage only saves the output
        # images and stores metadata — no heavy work.
        ssim_score: Optional[float] = None
        if ssim_result is not None:
            try:
                highlighted_rgb = cv2.cvtColor(
                    ssim_result.highlighted_image, cv2.COLOR_BGR2RGB
                )
                highlight_path = _unique_output_path("highlight_heatmap")
                Image.fromarray(highlighted_rgb).save(str(highlight_path))
                outputs["highlightHeatmap"] = str(
                    highlight_path.relative_to(OUTPUT_DIR.parent)
                )

                heatmap_rgb = cv2.cvtColor(
                    ssim_result.ssim_heatmap, cv2.COLOR_BGR2RGB
                )
                output_heatmap_path = _unique_output_path("output_heatmap")
                Image.fromarray(heatmap_rgb).save(str(output_heatmap_path))
                outputs["outputHeatmap"] = str(
                    output_heatmap_path.relative_to(OUTPUT_DIR.parent)
                )

                ssim_score = ssim_result.ssim_score
                outputs["ssimScore"] = ssim_score
                outputs["ssimInterpretation"] = ssim_result.interpretation
                outputs["changedRegions"] = len(ssim_result.changed_regions)

                logger.info(
                    "SSIM comparison: score=%.4f, regions=%d, verdict=%s",
                    ssim_score,
                    len(ssim_result.changed_regions),
                    ssim_result.interpretation,
                )
                audit.log_step(
                    service="ssim_comparison",
                    status="success",
                    input_data={"has_reference": True},
                    output_data={
                        "ssim_score": ssim_score,
                        "interpretation": ssim_result.interpretation,
                        "changed_regions": len(ssim_result.changed_regions),
                    },
                    # Latency already captured as part of the parallel wall time
                    latency=parallel_wall,
                )
            except Exception as exc:
                logger.warning("SSIM result processing failed: %s", exc)
                audit.log_step(
                    service="ssim_comparison",
                    status="failed",
                    error=str(exc),
                )

        # ── Stage 3c: SHAP intensity score ───────────────────────────
        #
        # Runs in a thread to avoid blocking the event loop.
        # Returns None when SHAP is unavailable or no detection is found.
        # visual_risk.py handles None gracefully (redistributes weight).
        shap_intensity_score: Optional[float] = None
        try:
            t0 = time.time()
            shap_intensity_score = await asyncio.to_thread(
                _extract_shap_intensity, detector, image
            )
            if shap_intensity_score is not None:
                outputs["shapIntensityScore"] = shap_intensity_score
                audit.log_step(
                    service="shap_explainer",
                    status="success",
                    input_data={"image_size": list(image.size)},
                    output_data={"shap_intensity_score": shap_intensity_score},
                    latency=time.time() - t0,
                )
            else:
                audit.log_step(
                    service="shap_explainer",
                    status="skipped",
                    output_data={"reason": "no detection or SHAP unavailable"},
                )
        except Exception as exc:
            logger.warning("SHAP step failed: %s", exc)
            audit.log_step(
                service="shap_explainer",
                status="failed",
                error=str(exc),
            )

        # ── Stage 4: Zero-shot inspection (always runs if enabled) ───
        inspector = get_zero_shot()
        if inspector is not None:
            try:
                t0 = time.time()
                zs_labels = manifest_items if manifest_items else list(DEFAULT_SCAN_LABELS)
                inspection = await asyncio.to_thread(
                    inspector.inspect, str(tmp_path), zs_labels
                )

                image_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                overlay = draw_inspection_overlay(image_bgr, inspection)
                overlay_path = _unique_output_path("zero_shot")
                cv2.imwrite(str(overlay_path), overlay)

                outputs["zeroShot"] = {
                    "overlayImage": str(
                        overlay_path.relative_to(OUTPUT_DIR.parent)
                    ),
                    "verdict": inspection.verdict.value,
                    "totalObjects": len(inspection.all_items),
                    "declaredCount": len(inspection.declared_items_found),
                    "undeclaredCount": len(inspection.undeclared_items),
                    "missingCount": len(inspection.missing_manifest_items),
                    "missingItems": inspection.missing_manifest_items,
                    "items": inspection.summary_table(),
                    "timings": {
                        k: round(v, 3) for k, v in inspection.timings.items()
                    },
                    "labelsUsed": zs_labels,
                }

                # Keep legacy fields for backward compat
                outputs["zeroShotOutputImage"] = outputs["zeroShot"]["overlayImage"]
                lines = [f"Verdict: {inspection.verdict.value}"]
                if inspection.missing_manifest_items:
                    lines.append(
                        f"Missing: {', '.join(inspection.missing_manifest_items)}"
                    )
                lines.append(f"Declared: {len(inspection.declared_items_found)}")
                lines.append(f"Undeclared: {len(inspection.undeclared_items)}")
                outputs["zeroShotOutputText"] = "\n".join(lines)

                audit.log_step(
                    service="zero_shot_inspection",
                    status="success",
                    input_data={"label_count": len(zs_labels), "labels": zs_labels},
                    output_data={
                        "verdict": inspection.verdict.value,
                        "total_objects": len(inspection.all_items),
                        "declared_count": len(inspection.declared_items_found),
                        "undeclared_count": len(inspection.undeclared_items),
                        "missing_count": len(inspection.missing_manifest_items),
                    },
                    latency=time.time() - t0,
                )
            except Exception as exc:
                logger.warning("Zero-shot inspection failed: %s", exc)
                audit.log_step(
                    service="zero_shot_inspection",
                    status="failed",
                    error=str(exc),
                )

        # ── Stage 5: Include manifest items in outputs if available ──
        if manifest_items:
            outputs["manifestItems"] = manifest_items

        # ── Stages 6–8: Composite risk scoring ───────────────────────
        #
        # Derive all inputs from the model outputs already computed above,
        # then call the new risk utils (no model I/O here).

        # suspicious_score — 1.0 if any YOLO-detected label is in the
        # combined threat set (prohibited ∪ suspicious), else 0.0
        detected_labels_lower = {d["label"].strip().lower() for d in raw_detections}
        suspicious_score = 1.0 if detected_labels_lower & _ALL_THREAT_LABELS else 0.0
        suspicious_flag = suspicious_score == 1.0

        # uncertain_ratio — from zero-shot: undeclared items / total detected.
        # Defaults to 0.0 when zero-shot did not run or found nothing.
        zs = outputs.get("zeroShot", {})
        total_objects = zs.get("totalObjects", 0)
        undeclared_count = zs.get("undeclaredCount", 0)
        uncertain_ratio = (
            undeclared_count / total_objects if total_objects > 0 else 0.0
        )

        # ssim_risk — convert the raw SSIM similarity score to a risk bucket.
        # ssim_score is None when no reference scan was uploaded.
        ssim_risk = ssim_score_to_risk(ssim_score)
        outputs["ssimRisk"] = ssim_risk

        # Stage 6: Visual risk
        visual_risk = compute_visual_risk(
            suspicious_score=suspicious_score,
            uncertain_ratio=uncertain_ratio,
            ssim_risk=ssim_risk,
            shap_intensity_score=shap_intensity_score,
        )

        # Stage 7–8: Data risk + final risk
        # data_risk is None until llm_extractor.py is wired in (Step 5).
        # compute_final_risk() handles None gracefully: final_risk = visual_risk.
        # TODO: replace None with compute_data_risk() output after Step 7.
        data_risk: Optional[float] = None
        final_risk, decision = compute_final_risk(data_risk, visual_risk)

        audit.log_step(
            service="composite_risk_scoring",
            status="success",
            input_data={
                "suspicious_score": suspicious_score,
                "uncertain_ratio": round(uncertain_ratio, 4),
                "ssim_risk": round(ssim_risk, 4),
                "shap_intensity_score": shap_intensity_score,
                "data_risk": data_risk,
            },
            output_data={
                "visual_risk": round(visual_risk, 4),
                "final_risk": final_risk,
                "decision": decision,
            },
        )

        # Augment the existing risk dict — all original fields (level, score,
        # reason, flags) are preserved; new fields are added alongside them.
        risk.update({
            "data_risk": data_risk,
            "visual_risk": round(visual_risk, 4),
            "final_risk": final_risk,
            "decision": decision,
            "risk_breakdown": {
                "suspicious_score": suspicious_score,
                "uncertain_ratio": round(uncertain_ratio, 4),
                "ssim_risk": round(ssim_risk, 4),
                "shap_intensity_score": shap_intensity_score,
                # Populated once llm_extractor.py is wired in
                "value_anomaly": None,
                "hs_code_risk": None,
                "country_risk": None,
            },
        })

        # ── Audit: finalize and save ────────────────────────────────
        audit_json = audit.finalize("success")
        logger.info(
            "✓ Audit saved: request_id=%s, steps=%d",
            audit.request_id,
            len(audit.steps),
        )

        # ── IPFS: upload audit JSON in background ─────────────────────
        if background_tasks is not None:
            background_tasks.add_task(
                _upload_audit_to_ipfs, audit_json, audit.request_id
            )

        return {
            "detections": detections,
            "risk": risk,
            "outputs": outputs if outputs else None,
            "suspicious_flag": suspicious_flag,
            "request_id": audit.request_id,
        }

    finally:
        # Clean up temp files
        for p in (tmp_path, tmp_ref_path, tmp_manifest_path):
            if p and p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass


def _upload_audit_to_ipfs(audit_json: dict, request_id: str) -> None:
    """Background task: upload audit to IPFS, then store CID in Supabase."""
    cid = None
    try:
        encrypted_string = encrypt_data(audit_json)
        secure_payload = {"encrypted_payload": encrypted_string}
        cid = upload_to_ipfs(secure_payload, name=request_id)
        logger.info("✓ IPFS upload complete: request_id=%s, CID=%s", request_id, cid)
    except Exception as exc:
        logger.error("✗ IPFS upload failed for request_id=%s: %s", request_id, exc)
        return

    try:
        status = audit_json.get("final_status", "success")
        step_names = [s.get("service", "") for s in audit_json.get("steps", [])]
        description = f"Pipeline: {', '.join(step_names)}. Status: {status}"
        store_audit_metadata(
            cid=cid,
            request_id=request_id,
            status=status,
            description=description,
        )
        logger.info("✓ Supabase metadata stored: request_id=%s", request_id)
    except Exception as exc:
        logger.error(
            "✗ Supabase insert failed for request_id=%s: %s", request_id, exc
        )


# ── Endpoint: Audits ───────────────────────────────────────────────────

@app.get("/api/audit/logs")
async def get_all_audits(limit: Optional[int] = Query(None, description="Max logs to return (leave blank for all)"), date_filter: Optional[str] = Query(None, description="Filter by date in DD-MM-YYYY format (e.g. 04-04-2026)")):
    """Fetch a list of all audit metadata from Supabase, optionally filtered by date."""
    try:
        formatted_date = None
        if date_filter:
            # Convert DD-MM-YYYY to YYYY-MM-DD for database query
            try:
                date_obj = datetime.strptime(date_filter, "%d-%m-%Y")
                formatted_date = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Please use DD-MM-YYYY (e.g. 04-04-2026)")

        records = query_audits(limit=limit, date_filter=formatted_date)
        return {"logs": records}
    except Exception as exc:
        logger.error("Failed to query audit logs: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch audit logs from database")


@app.get("/api/audit/logs/{request_id}")
async def get_audit_by_request_id(request_id: str):
    """
    Fetch the detailed audit log using the request_id.
    Queries Supabase to find the CID, pulls the encrypted JSON from Pinata IPFS, and decrypts it.
    """
    try:
        # 1. Look up the CID in Supabase using the request_id
        db_records = query_audits(request_id=request_id)
        if not db_records:
            raise HTTPException(status_code=404, detail=f"No audit found for request_id: {request_id}")
            
        cid = db_records[0].get("cid")
        if not cid:
            raise ValueError("Database record missing CID")

        # 2. Fetch encrypted blob from IPFS using the CID
        secure_payload = fetch_from_ipfs(cid)
        
        # 3. Extract encrypted string (handle backwards compatibility)
        encrypted_string = secure_payload.get("encrypted_payload")
        
        if not encrypted_string:
            # If it doesn't have an encrypted payload, it might be an older 
            # scan from before we enabled encryption. Return it as-is.
            return {"audit": secure_payload}
            
        # 4. Decrypt back to readable JSON
        decrypted_json = decrypt_data(encrypted_string)
        
        return {
            "audit": decrypted_json,
            "metadata": db_records[0] # include the db metadata (timestamp, etc.)
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch or decrypt audit for request_id %s: %s", request_id, exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve or decrypt the audit package")


# ── Endpoint: POST /api/manifest/extract ───────────────────────────────


def _extract_items_from_pdf(pdf_path: Path) -> list[str]:
    """
    Extract cargo item names from a manifest PDF.

    Uses pdfplumber for text extraction, then applies simple heuristics
    to pull out item-like lines.  Falls back to an empty list on failure.
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error(
            "pdfplumber is not installed. Install it: pip install pdfplumber"
        )
        return []

    items: list[str] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

            if not full_text.strip():
                return []

            skip_prefixes = (
                "total", "subtotal", "page", "date", "invoice",
                "bill", "shipping", "consignee", "shipper",
                "description", "qty", "quantity", "weight",
                "value", "hs code", "country", "origin",
            )
            for line in full_text.splitlines():
                cleaned = line.strip()
                if not cleaned:
                    continue
                if len(cleaned) < 2 or len(cleaned) > 200:
                    continue
                lower = cleaned.lower()
                if any(lower.startswith(prefix) for prefix in skip_prefixes):
                    continue
                if cleaned.replace(".", "").replace(",", "").replace(" ", "").isdigit():
                    continue
                items.append(cleaned)

    except Exception as exc:
        logger.warning("PDF extraction failed: %s", exc)

    return items


@app.post("/api/manifest/extract")
async def manifest_extract(file: UploadFile = File(...)):
    """
    Parse a manifest PDF and return extracted cargo item names.

    Response: {"items": ["item1", "item2", ...]}
    """
    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")

    tmp_path: Optional[Path] = None
    try:
        tmp_path = _save_upload_to_temp(file, suffix=".pdf")
        items = _extract_items_from_pdf(tmp_path)
        return {"items": items}
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


# ── Endpoint: GET /api/files ───────────────────────────────────────────


@app.get("/api/files")
def serve_file(path: str = Query(..., description="Relative path to the file")):
    """
    Serve a file from the output directory.

    Security: only allows files under OUTPUT_DIR's parent directory.
    Blocks path traversal (.. and absolute paths).
    """
    if ".." in path or path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")

    candidate = Path(path).as_posix().lstrip("/")
    full_path = (OUTPUT_DIR.parent / candidate).resolve()

    allowed_root = OUTPUT_DIR.parent.resolve()
    if allowed_root not in full_path.parents and full_path != allowed_root:
        raise HTTPException(status_code=400, detail="Path outside allowed directory")

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    mime, _ = mimetypes.guess_type(str(full_path))
    return FileResponse(str(full_path), media_type=mime or "application/octet-stream")


# ── Health check ───────────────────────────────────────────────────────


@app.get("/api/health")
def health():
    """Simple health check — confirms the server is up."""
    return {
        "status": "ok",
        "model_path": MODEL_PATH,
        "output_dir": str(OUTPUT_DIR),
        "zero_shot_enabled": ENABLE_ZERO_SHOT,
        "shap_available": SHAP_AVAILABLE,
    }
