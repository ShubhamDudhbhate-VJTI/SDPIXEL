"""
main.py — FastAPI server for the Customs X-ray Intelligence Platform.

Bridges the React frontend to the existing Python ML utilities:
  - XRayDetector     (YOLOv8 object detection)
  - generate_gradcam (pseudo Grad-CAM heatmap)
  - calculate_risk   (risk scoring)
  - ZeroShotManifestInspector (OWL-ViT v2 + SAM 2)
  - draw_inspection_overlay   (annotated zero-shot image)

Endpoints:
  POST /api/analyze           — run full pipeline on an uploaded X-ray scan
  POST /api/manifest/extract  — extract item list from a manifest PDF
  GET  /api/files?path=...    — serve generated output files
"""

from __future__ import annotations
from utils.shap_explainer import YOLOShapExplainer

import logging
import mimetypes
import os
import shutil
import tempfile
import time
import uuid
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
from utils.ipfs_client import upload_to_ipfs
from utils.supabase_client import store_audit_metadata
from utils.encryption import encrypt_data
from utils.gradcam import generate_gradcam, overlay_heatmap
from utils.image_comparator import compare_scans
from utils.risk_scorer import calculate_risk
from utils.zero_shot_inspector import (
    DEFAULT_SCAN_LABELS,
    ZeroShotManifestInspector,
    draw_inspection_overlay,
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

    Returns {detections, risk, outputs} matching the frontend contract.
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

        # --- 1. YOLOv8 detection ---
        detector = get_detector()
        t0 = time.time()
        raw_detections = detector.detect(image)
        detection_latency = time.time() - t0
        detections = _transform_detections(raw_detections)

        audit.log_step(
            service="yolov8_detection",
            status="success",
            input_data={"filename": file.filename, "image_size": list(image.size)},
            output_data={
                "detection_count": len(detections),
                "labels": [d["label"] for d in detections],
            },
            latency=detection_latency,
            model_version=MODEL_PATH,
        )

        # --- 2. Risk scoring ---
        t0 = time.time()
        risk = calculate_risk(raw_detections)
        audit.log_step(
            service="risk_scoring",
            status="success",
            input_data={"detection_count": len(raw_detections)},
            output_data={"level": risk.get("level"), "score": risk.get("score")},
            latency=time.time() - t0,
        )

        # --- 3. Grad-CAM heatmap + highlight/output heatmaps ---
        outputs: dict = {}
        try:
            t0 = time.time()
            # Generate the blended overlay (60% original + 40% heatmap)
            gradcam_image = generate_gradcam(MODEL_PATH, image)
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

        # --- 3b. SSIM image comparison (when reference scan is provided) ---
        if tmp_ref_path is not None:
            try:
                t0 = time.time()
                ref_image = Image.open(str(tmp_ref_path)).convert("RGB")
                comparison = compare_scans(image, ref_image)

                # highlightHeatmap — current scan with red boxes on changed regions
                highlighted_rgb = cv2.cvtColor(
                    comparison.highlighted_image, cv2.COLOR_BGR2RGB
                )
                highlight_path = _unique_output_path("highlight_heatmap")
                Image.fromarray(highlighted_rgb).save(str(highlight_path))
                outputs["highlightHeatmap"] = str(
                    highlight_path.relative_to(OUTPUT_DIR.parent)
                )

                # outputHeatmap — JET-colorized SSIM difference map
                heatmap_rgb = cv2.cvtColor(
                    comparison.ssim_heatmap, cv2.COLOR_BGR2RGB
                )
                output_heatmap_path = _unique_output_path("output_heatmap")
                Image.fromarray(heatmap_rgb).save(str(output_heatmap_path))
                outputs["outputHeatmap"] = str(
                    output_heatmap_path.relative_to(OUTPUT_DIR.parent)
                )

                # Include SSIM metadata
                outputs["ssimScore"] = comparison.ssim_score
                outputs["ssimInterpretation"] = comparison.interpretation
                outputs["changedRegions"] = len(comparison.changed_regions)

                logger.info(
                    "SSIM comparison: score=%.4f, regions=%d, verdict=%s",
                    comparison.ssim_score,
                    len(comparison.changed_regions),
                    comparison.interpretation,
                )

                audit.log_step(
                    service="ssim_comparison",
                    status="success",
                    input_data={"has_reference": True},
                    output_data={
                        "ssim_score": comparison.ssim_score,
                        "interpretation": comparison.interpretation,
                        "changed_regions": len(comparison.changed_regions),
                    },
                    latency=time.time() - t0,
                )
            except Exception as exc:
                logger.warning("SSIM comparison failed: %s", exc)
                audit.log_step(
                    service="ssim_comparison",
                    status="failed",
                    error=str(exc),
                )

        # --- 4. Zero-shot inspection (always runs if enabled) ---
        inspector = get_zero_shot()
        if inspector is not None:
            try:
                t0 = time.time()
                # Use manifest items if available, otherwise default scan labels
                zs_labels = manifest_items if manifest_items else list(DEFAULT_SCAN_LABELS)
                inspection = inspector.inspect(str(tmp_path), zs_labels)

                # Save annotated overlay image
                image_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                overlay = draw_inspection_overlay(image_bgr, inspection)
                overlay_path = _unique_output_path("zero_shot")
                cv2.imwrite(str(overlay_path), overlay)

                # Build structured zero-shot response
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

        # --- 5. Include manifest items in outputs if available ---
        if manifest_items:
            outputs["manifestItems"] = manifest_items

        # ── Audit: finalize and save ────────────────────────────────
        audit_json = audit.finalize("success")
        logger.info("✓ Audit saved: request_id=%s, steps=%d", audit.request_id, len(audit.steps))

        # ── IPFS: upload audit JSON in background ─────────────────────
        if background_tasks is not None:
            background_tasks.add_task(_upload_audit_to_ipfs, audit_json, audit.request_id)

        return {
            "detections": detections,
            "risk": risk,
            "outputs": outputs if outputs else None,
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
        # Encrypt the audit dictionary before uploading it to public IPFS
        encrypted_string = encrypt_data(audit_json)
        
        # Package it so it's still technically a valid JSON object structure for Pinata, 
        # but the content is just an encrypted string.
        secure_payload = {"encrypted_payload": encrypted_string}
        
        cid = upload_to_ipfs(secure_payload, name=request_id)
        logger.info("✓ IPFS upload complete: request_id=%s, CID=%s", request_id, cid)
    except Exception as exc:
        logger.error("✗ IPFS upload failed for request_id=%s: %s", request_id, exc)
        return

    # Store CID + metadata in Supabase
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
        logger.error("✗ Supabase insert failed for request_id=%s: %s", request_id, exc)


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

            # Heuristic: each non-empty line that looks like an item name
            # Skip lines that look like headers, totals, or metadata
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
                # Skip lines that are purely numeric or very short codes
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
    # Basic traversal prevention
    if ".." in path or path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")

    candidate = Path(path).as_posix().lstrip("/")
    full_path = (OUTPUT_DIR.parent / candidate).resolve()

    # Ensure the resolved path is within the allowed root
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
    }
