"""
zero_shot_inspector.py — V2 Zero-Shot Cargo Manifest Inspector
================================================================
Architecture: OWL-ViT v2 (open-vocabulary detection) + SAM 2 (segmentation)

Key improvements over V1 (Grounding DINO):
  - Per-label iterative detection eliminates the "label clumping" bug
  - Native missing-item detection via per-query scoring
  - Pure pip install — no git clone or C++ compilation needed
  - Cargo verdict system (CLEAR / UNDECLARED / MISSING / MIXED)

Pipeline:
  1. Per-label detection: run OWL-ViT v2 for each manifest label individually
  2. Generic scene sweep: detect all physical objects with broad queries
  3. NMS deduplication: remove overlapping boxes within and across labels
  4. IoU reconciliation: match generic objects vs labeled detections
  5. Missing item check: flag manifest labels with zero visual matches
  6. SAM 2 segmentation: pixel-precise masks for every indexed object
  7. Structured output with cargo verdict
"""

from __future__ import annotations

import logging
import time
import warnings
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# Suppress harmless torch.classes instantiation warning
warnings.filterwarnings(
    "ignore",
    message=".*Tried to instantiate class.*__path__._path.*",
)

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision.ops import nms, box_iou
from transformers import Owlv2Processor, Owlv2ForObjectDetection
from ultralytics import SAM

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

OWL_MODEL_ID = "google/owlv2-base-patch16-ensemble"
SAM_MODEL_ID = "sam2_b.pt"

# Default sweep queries for the "find everything" pass.
# Designed for X-ray cargo scans — domain-specific hints for dense imagery.
# Users can override these live from the Streamlit UI.
DEFAULT_SWEEP_QUERIES = [
    "X-ray of a physical object",
    "X-ray of a gun",
    "X-ray of a bomb",
    "X-ray of a blade",
    "X-ray of a knife",
    "X-ray of a pepper spray",
    "X-ray of a taser",
    "X-ray of a stun gun",
    "X-ray of a taser gun",
    "X-ray of a taser gun",
    "X-ray of a human",
    "X-ray of a box",
    "X-ray of a bag",
    "X-ray of an electronic device",
    "X-ray of a laptop or computer",
    "X-ray of a phone or tablet",
    "X-ray of a cable or wire",
    "X-ray of a bottle or liquid container",
    "X-ray of a weapon or knife",
    "X-ray of clothing or shoes",
    "X-ray of a material or substance",
    "X-ray of a metal or metallic object",
    "X-ray of a wire bundle",
]

DEFAULT_BOX_THRESHOLD = 0.25
DEFAULT_TEXT_THRESHOLD = 0.30
DEFAULT_IOU_MATCH_THRESHOLD = 0.20
DEFAULT_NMS_THRESHOLD = 0.30

# Default manifest-style labels used when no manifest PDF is provided.
# These are concrete cargo item categories for the per-label detection pass.
DEFAULT_SCAN_LABELS = [
    "electronics",
    "laptop",
    "phone",
    "cables",
    "clothing",
    "shoes",
    "food items",
    "bottles",
    "tools",
    "weapons",
    "drugs",
    "metal objects",
    "packages",
    "documents",
]


# ═══════════════════════════════════════════════════════════════════════════
# Enums & data structures
# ═══════════════════════════════════════════════════════════════════════════

class CargoVerdict(str, Enum):
    """High-level cargo scan outcome."""
    CLEAR = "CLEAR"
    UNDECLARED_ITEMS = "UNDECLARED ITEMS DETECTED"
    MISSING_DECLARED_GOODS = "SUSPICIOUS: MISSING DECLARED GOODS — REQUIRES HUMAN INSPECTION"
    MIXED = "CRITICAL: UNDECLARED ITEMS + MISSING DECLARED GOODS"


@dataclass
class DetectedItem:
    """Single detected physical item with persistent index."""
    index: int
    status: str              # "declared" | "undeclared"
    label: str               # Matched manifest label or generic description
    confidence: float
    bbox: list[float]        # [x1, y1, x2, y2] pixel coords
    mask: Optional[np.ndarray] = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "status": self.status,
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "bbox": [round(c, 2) for c in self.bbox],
        }


@dataclass
class InspectionResult:
    """Full inspection output."""
    declared_items_found: list[DetectedItem]
    undeclared_items: list[DetectedItem]
    missing_manifest_items: list[str]       # Labels in manifest but NOT found
    all_items: list[DetectedItem]
    manifest_labels: list[str]
    verdict: CargoVerdict
    timings: dict[str, float]               # Per-stage latency in seconds

    def summary_table(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.all_items]


# ═══════════════════════════════════════════════════════════════════════════
# Main Inspector
# ═══════════════════════════════════════════════════════════════════════════

class ZeroShotManifestInspector:
    """
    OWL-ViT v2 based zero-shot cargo manifest inspector.

    Usage::

        inspector = ZeroShotManifestInspector()
        result = inspector.inspect("scan.png", ["laptop", "shoes", "cables"])
        print(result.verdict)
        print(result.summary_table())
    """

    def __init__(
        self,
        owl_model_id: str = OWL_MODEL_ID,
        sam_model_id: str = SAM_MODEL_ID,
        device: str | None = None,
    ) -> None:
        # ── Device selection ────────────────────────────────────────────
        # Priority: CUDA → MPS (Apple Silicon) → CPU
        if device:
            self.device = device
        elif torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = "mps"
            # Enable MPS fallback for ops not yet supported on Metal
            import os
            os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        else:
            self.device = "cpu"

        logger.info("Loading OWL-ViT v2 from %s …", owl_model_id)
        self.processor = Owlv2Processor.from_pretrained(owl_model_id)
        try:
            self.owl_model = Owlv2ForObjectDetection.from_pretrained(owl_model_id).to(self.device)
        except Exception as exc:
            logger.warning("Failed to load OWL-ViT on %s, falling back to CPU: %s", self.device, exc)
            self.device = "cpu"
            self.owl_model = Owlv2ForObjectDetection.from_pretrained(owl_model_id).to("cpu")
        self.owl_model.eval()

        # SAM 2 — force CPU on MPS (SAM's mask decoder uses ops not
        # supported on Metal: grid_sampler, some scatter ops, etc.)
        logger.info("Loading SAM 2 (%s) …", sam_model_id)
        if self.device == "mps":
            logger.info("SAM 2 forced to CPU (MPS not fully supported for SAM)")
            self.sam_model = SAM(sam_model_id)
            # ultralytics SAM auto-selects device; override to CPU
            if hasattr(self.sam_model, 'model') and hasattr(self.sam_model.model, 'to'):
                try:
                    self.sam_model.model.to("cpu")
                except Exception:
                    pass
        else:
            self.sam_model = SAM(sam_model_id)

        logger.info("✓ Models loaded — OWL-ViT on %s, SAM on %s",
                     self.device, "cpu" if self.device == "mps" else self.device)

    # ── Public API ──────────────────────────────────────────────────────

    def inspect(
        self,
        image_path: str | Path,
        manifest_labels: list[str],
        *,
        sweep_queries: list[str] | None = None,
        box_threshold: float = DEFAULT_BOX_THRESHOLD,
        text_threshold: float = DEFAULT_TEXT_THRESHOLD,
        iou_match_threshold: float = DEFAULT_IOU_MATCH_THRESHOLD,
        nms_threshold: float = DEFAULT_NMS_THRESHOLD,
        use_iterative: bool = True,
    ) -> InspectionResult:
        """
        Run the full inspection pipeline.

        Parameters
        ----------
        image_path : path to the X-ray scan.
        manifest_labels : list of declared item strings.
        sweep_queries : domain-specific prompts for the generic sweep pass.
                        If None, uses DEFAULT_SWEEP_QUERIES.
        box_threshold : minimum objectness score for OWL-ViT boxes.
        text_threshold : minimum text-similarity for label assignment.
        iou_match_threshold : IoU above which generic→labeled match is declared.
        nms_threshold : IoU threshold for NMS deduplication.
        use_iterative : if True, run per-label detection (anti-clumping).
        """
        image_path = str(image_path)
        image = Image.open(image_path).convert("RGB")
        timings: dict[str, float] = {}
        active_sweep = sweep_queries if sweep_queries is not None else DEFAULT_SWEEP_QUERIES

        # ── Pass 1: Domain-Specific Sweep (Find All) ───────────────────
        t0 = time.perf_counter()
        generic_boxes, generic_scores, generic_labels = (
            self._detect_batch(image, active_sweep, box_threshold)
        )
        timings["sweep_detection"] = time.perf_counter() - t0

        # ── Pass 2: Manifest Sweep (Verify) ────────────────────────────
        # Use a LOWER threshold for manifest items to maximize recall.
        # Manifest labels are specific → we'd rather get false positives
        # (which IoU reconciliation will handle) than miss real items.
        manifest_threshold = max(box_threshold * 0.5, 0.01)
        t0 = time.perf_counter()
        if use_iterative and manifest_labels:
            manifest_boxes, manifest_scores, manifest_labels_out = (
                self._detect_per_label(image, manifest_labels, manifest_threshold)
            )
        elif manifest_labels:
            manifest_boxes, manifest_scores, manifest_labels_out = (
                self._detect_batch(image, manifest_labels, manifest_threshold)
            )
        else:
            manifest_boxes = torch.zeros((0, 4))
            manifest_scores = torch.zeros(0)
            manifest_labels_out = []
        timings["manifest_detection"] = time.perf_counter() - t0

        # ── Step 3: NMS deduplication ──────────────────────────────────
        t0 = time.perf_counter()
        manifest_boxes, manifest_scores, manifest_labels_out = self._apply_nms(
            manifest_boxes, manifest_scores, manifest_labels_out, nms_threshold,
        )
        generic_boxes, generic_scores, generic_labels = self._apply_nms(
            generic_boxes, generic_scores, generic_labels, nms_threshold,
        )
        timings["nms"] = time.perf_counter() - t0

        # ── Step 4: IoU reconciliation ─────────────────────────────────
        t0 = time.perf_counter()
        items, found_manifest_labels = self._reconcile(
            generic_boxes, generic_scores, generic_labels,
            manifest_boxes, manifest_scores, manifest_labels_out,
            iou_match_threshold, manifest_labels,
        )
        timings["reconciliation"] = time.perf_counter() - t0

        # ── Step 5: Missing manifest items ─────────────────────────────
        found_set = {l.strip().lower() for l in found_manifest_labels}
        missing = [
            lbl for lbl in manifest_labels
            if lbl.strip().lower() not in found_set
        ]

        # ── Step 6: SAM 2 segmentation ─────────────────────────────────
        t0 = time.perf_counter()
        if items:
            all_bboxes = [item.bbox for item in items]
            masks = self._segment(image_path, all_bboxes, image.height, image.width)
            for item, mask in zip(items, masks):
                item.mask = mask
        timings["segmentation"] = time.perf_counter() - t0

        # ── Step 7: Verdict ────────────────────────────────────────────
        has_undeclared = any(it.status == "undeclared" for it in items)
        has_missing = len(missing) > 0

        if has_undeclared and has_missing:
            verdict = CargoVerdict.MIXED
        elif has_missing:
            verdict = CargoVerdict.MISSING_DECLARED_GOODS
        elif has_undeclared:
            verdict = CargoVerdict.UNDECLARED_ITEMS
        else:
            verdict = CargoVerdict.CLEAR

        timings["total"] = sum(v for k, v in timings.items() if k != "total")

        declared = [it for it in items if it.status == "declared"]
        undeclared = [it for it in items if it.status == "undeclared"]

        logger.info(
            "Inspection complete: %d declared, %d undeclared, %d missing → %s",
            len(declared), len(undeclared), len(missing), verdict.value,
        )

        return InspectionResult(
            declared_items_found=declared,
            undeclared_items=undeclared,
            missing_manifest_items=missing,
            all_items=items,
            manifest_labels=manifest_labels,
            verdict=verdict,
            timings=timings,
        )

    # ── Detection strategies ────────────────────────────────────────────

    def _detect_per_label(
        self,
        image: Image.Image,
        labels: list[str],
        threshold: float,
    ) -> tuple[torch.Tensor, torch.Tensor, list[str]]:
        """
        Anti-clumping strategy: run OWL-ViT v2 once per manifest label.
        Each box is guaranteed to map to exactly ONE label.

        Uses MULTIPLE prompt variants per label for maximum recall on X-ray images.
        """
        all_boxes, all_scores, all_labels = [], [], []

        for label in labels:
            clean_label = label.strip()
            # Multiple prompt variants — X-rays are NOT photos, so we try
            # several framings and keep the best detections across all.
            prompts = [
                clean_label,                          # bare label                   # simple article
                f"an x-ray of {clean_label}",         # domain-specific
                f"a scan showing {clean_label}",      # scan context
            ]

            best_boxes, best_scores = [], []

            for prompt in prompts:
                text_queries = [[prompt]]
                inputs = self.processor(
                    text=text_queries, images=image, return_tensors="pt"
                ).to(self.device)

                with torch.no_grad():
                    outputs = self.owl_model(**inputs)

                target_sizes = torch.tensor(
                    [(image.height, image.width)], device=self.device
                )
                results = self.processor.post_process_grounded_object_detection(
                    outputs=outputs,
                    target_sizes=target_sizes,
                    threshold=threshold,
                    text_labels=text_queries,
                )[0]

                boxes = results["boxes"]
                scores = results["scores"]

                if len(boxes) > 0:
                    best_boxes.append(boxes.cpu())
                    best_scores.append(scores.cpu())

            # Merge detections from all prompt variants, then NMS
            if best_boxes:
                merged_boxes = torch.cat(best_boxes, dim=0)
                merged_scores = torch.cat(best_scores, dim=0)

                # NMS across prompt variants for this label
                if len(merged_boxes) > 1:
                    keep = nms(merged_boxes.float(), merged_scores.float(), 0.5)
                    merged_boxes = merged_boxes[keep]
                    merged_scores = merged_scores[keep]

                all_boxes.append(merged_boxes)
                all_scores.append(merged_scores)
                all_labels.extend([clean_label] * len(merged_boxes))

        if all_boxes:
            return (
                torch.cat(all_boxes, dim=0),
                torch.cat(all_scores, dim=0),
                all_labels,
            )
        return torch.zeros((0, 4)), torch.zeros(0), []

    def _detect_batch(
        self,
        image: Image.Image,
        labels: list[str],
        threshold: float,
    ) -> tuple[torch.Tensor, torch.Tensor, list[str]]:
        """
        Batch strategy: pass all queries at once (faster, but may clump).
        Uses bare labels — no 'a photo of' prefix for X-ray compatibility.
        """
        if not labels:
            return torch.zeros((0, 4)), torch.zeros(0), []

        clean_labels = [l.strip() for l in labels]
        text_queries = [clean_labels]
        inputs = self.processor(
            text=text_queries, images=image, return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            outputs = self.owl_model(**inputs)

        target_sizes = torch.tensor(
            [(image.height, image.width)], device=self.device
        )
        results = self.processor.post_process_grounded_object_detection(
            outputs=outputs,
            target_sizes=target_sizes,
            threshold=threshold,
            text_labels=text_queries,
        )[0]

        boxes = results["boxes"].cpu()
        scores = results["scores"].cpu()
        out_labels = [lbl.strip() for lbl in results["text_labels"]]

        return boxes, scores, out_labels

    # ── NMS ─────────────────────────────────────────────────────────────

    @staticmethod
    def _apply_nms(
        boxes: torch.Tensor,
        scores: torch.Tensor,
        labels: list[str],
        iou_threshold: float,
    ) -> tuple[torch.Tensor, torch.Tensor, list[str]]:
        """Apply class-agnostic NMS to remove duplicate boxes."""
        if len(boxes) == 0:
            return boxes, scores, labels

        keep = nms(boxes.float(), scores.float(), iou_threshold)
        return (
            boxes[keep],
            scores[keep],
            [labels[i] for i in keep.tolist()],
        )

    # ── IoU reconciliation ──────────────────────────────────────────────

    def _reconcile(
        self,
        gen_boxes: torch.Tensor,
        gen_scores: torch.Tensor,
        gen_labels: list[str],
        man_boxes: torch.Tensor,
        man_scores: torch.Tensor,
        man_labels: list[str],
        iou_threshold: float,
        original_manifest: list[str],
    ) -> tuple[list[DetectedItem], list[str]]:
        """
        Cross-reference generic vs manifest detections.

        Returns (items, found_manifest_labels).
        """
        items: list[DetectedItem] = []
        found_manifest_labels: list[str] = []
        idx = 0

        # First, add all manifest detections as declared
        used_manifest_indices: set[int] = set()
        for i in range(len(man_boxes)):
            bbox = man_boxes[i].tolist()
            conf = man_scores[i].item()
            raw_label = man_labels[i]
            # Resolve to the best-matching original manifest label
            label = self._best_manifest_match(raw_label, original_manifest)

            # Deduplicate: skip if overlapping with already-added declared item
            skip = False
            for existing in items:
                iou_val = self._single_iou(bbox, existing.bbox)
                if iou_val >= iou_threshold:
                    skip = True
                    break
            if skip:
                continue

            items.append(DetectedItem(
                index=idx, status="declared",
                label=label, confidence=conf, bbox=bbox,
            ))
            found_manifest_labels.append(label)
            used_manifest_indices.add(i)
            idx += 1

        # Then, check each generic detection
        for i in range(len(gen_boxes)):
            bbox = gen_boxes[i].tolist()
            conf = gen_scores[i].item()
            g_label = gen_labels[i]

            # Check 1: IoU overlap with any declared item from manifest pass
            overlaps_declared = False
            for existing in items:
                if existing.status == "declared":
                    iou_val = self._single_iou(bbox, existing.bbox)
                    if iou_val >= iou_threshold:
                        overlaps_declared = True
                        break

            if overlaps_declared:
                continue  # Skip — already covered by a manifest detection

            # Check 2: Does this sweep label TEXT-MATCH a manifest label?
            # This is the safety net: even if Pass 2 missed this item
            # (low scores), the sweep found it with a matching label.
            matched_manifest = self._best_manifest_match(g_label, original_manifest)
            if matched_manifest.lower() != g_label.strip().lower():
                # It matched a manifest label → declared
                items.append(DetectedItem(
                    index=idx, status="declared",
                    label=matched_manifest, confidence=conf, bbox=bbox,
                ))
                found_manifest_labels.append(matched_manifest)
                idx += 1
            else:
                # Check 3: Also check IoU overlap with manifest boxes directly
                matched_via_iou = False
                for j in range(len(man_boxes)):
                    m_bbox = man_boxes[j].tolist()
                    iou_val = self._single_iou(bbox, m_bbox)
                    if iou_val >= iou_threshold:
                        matched_label = self._best_manifest_match(
                            man_labels[j], original_manifest
                        )
                        items.append(DetectedItem(
                            index=idx, status="declared",
                            label=matched_label, confidence=conf, bbox=bbox,
                        ))
                        found_manifest_labels.append(matched_label)
                        matched_via_iou = True
                        idx += 1
                        break

                if not matched_via_iou:
                    # Truly undeclared — no text match, no IoU match
                    items.append(DetectedItem(
                        index=idx, status="undeclared",
                        label=g_label, confidence=conf, bbox=bbox,
                    ))
                    idx += 1

        return items, found_manifest_labels

    @staticmethod
    def _single_iou(box_a: list[float], box_b: list[float]) -> float:
        """Compute IoU between two xyxy boxes."""
        x1 = max(box_a[0], box_b[0])
        y1 = max(box_a[1], box_b[1])
        x2 = min(box_a[2], box_b[2])
        y2 = min(box_a[3], box_b[3])

        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
        union = area_a + area_b - inter

        return inter / max(union, 1e-6)

    @staticmethod
    def _best_manifest_match(phrase: str, manifest_labels: list[str]) -> str:
        """
        Map a detected phrase back to the best-matching manifest label
        via substring containment (ported from V1 for better label resolution).
        """
        p = phrase.strip().lower()
        for label in manifest_labels:
            ll = label.strip().lower()
            if ll in p or p in ll:
                return label.strip()
        return phrase.strip()

    # ── SAM 2 segmentation ──────────────────────────────────────────────

    def _segment(
        self,
        image_path: str,
        bboxes: list[list[float]],
        img_h: int,
        img_w: int,
    ) -> list[np.ndarray]:
        """Generate SAM 2 masks from bounding boxes."""
        if not bboxes:
            return []

        results = self.sam_model(image_path, bboxes=bboxes)
        masks: list[np.ndarray] = []

        if results and results[0].masks is not None:
            mask_data = results[0].masks.data
            for i in range(mask_data.shape[0]):
                m = mask_data[i].cpu().numpy().astype(np.uint8) * 255
                masks.append(m)

        # Pad with empty masks if SAM returned fewer than expected
        while len(masks) < len(bboxes):
            masks.append(np.zeros((img_h, img_w), dtype=np.uint8))

        return masks[:len(bboxes)]


# ═══════════════════════════════════════════════════════════════════════════
# Visualization — per-item distinct color palette
# ═══════════════════════════════════════════════════════════════════════════

# 12-color palette (BGR for OpenCV) — each item gets a unique color.
# Declared items use full saturation; undeclared items get a red-tinted variant.
ITEM_COLORS_BGR = [
    (230, 160,  20),   # Vivid blue
    ( 50, 205,  50),   # Lime green
    (  0, 200, 200),   # Yellow / gold
    (200,  80, 200),   # Magenta / pink
    ( 80, 200, 255),   # Orange
    (200, 200,  50),   # Cyan
    (100, 100, 255),   # Coral / salmon
    ( 50, 220, 130),   # Spring green
    (255, 140,  60),   # Light blue
    (128,  50, 200),   # Purple
    (  0, 180, 180),   # Olive / dark yellow
    (180, 120, 255),   # Peach / light pink
]

COLOR_UNDECLARED_HIGHLIGHT = (0, 0, 255)  # Bright red border for undeclared
MASK_ALPHA = 0.35
FONT = cv2.FONT_HERSHEY_SIMPLEX


def _get_item_color(index: int) -> tuple[int, int, int]:
    """Cycle through the palette by item index."""
    return ITEM_COLORS_BGR[index % len(ITEM_COLORS_BGR)]


def draw_inspection_overlay(
    image: np.ndarray,
    result: InspectionResult,
    *,
    mask_alpha: float = MASK_ALPHA,
) -> np.ndarray:
    """
    Draw masks + labeled bounding boxes on a BGR image.
    Each item gets a distinct color from the palette.
    Declared = solid 2px border. Undeclared = thick 3px red-highlighted border.
    """
    overlay = image.copy()
    output = image.copy()

    for item in result.all_items:
        is_declared = item.status == "declared"
        color = _get_item_color(item.index)

        # Mask color: per-item unique color
        mask_color = color
        # For undeclared items, tint the mask toward red
        if not is_declared:
            mask_color = (
                max(0, color[0] // 2),
                max(0, color[1] // 3),
                min(255, color[2] + 80),
            )

        # Box color: unique per item, but undeclared gets a red outer border
        box_color = color
        box_thickness = 2

        # Mask
        if item.mask is not None:
            binary = item.mask > 127
            if binary.shape[:2] != overlay.shape[:2]:
                binary = cv2.resize(
                    item.mask, (overlay.shape[1], overlay.shape[0]),
                    interpolation=cv2.INTER_NEAREST,
                ) > 127
            overlay[binary] = mask_color

        # Bounding box
        x1, y1, x2, y2 = [int(c) for c in item.bbox]

        # Undeclared: draw a thick red border underneath, then the item color on top
        if not is_declared:
            cv2.rectangle(output, (x1 - 1, y1 - 1), (x2 + 1, y2 + 1),
                          COLOR_UNDECLARED_HIGHLIGHT, 4)
        cv2.rectangle(output, (x1, y1), (x2, y2), box_color, box_thickness)

        # Label
        tag = "✓ DECLARED" if is_declared else "⚠ UNDECLARED"
        text = f"[{item.index}] {item.label} ({item.confidence:.0%}) {tag}"
        fs, th = 0.42, 1
        (tw, tht), bl = cv2.getTextSize(text, FONT, fs, th)

        # Background: item color for declared, red for undeclared
        bg_color = box_color if is_declared else COLOR_UNDECLARED_HIGHLIGHT
        cv2.rectangle(
            output,
            (x1, max(y1 - tht - bl - 6, 0)),
            (x1 + tw + 6, y1),
            bg_color, cv2.FILLED,
        )
        cv2.putText(
            output, text,
            (x1 + 3, max(y1 - bl - 3, tht + 3)),
            FONT, fs, (255, 255, 255), th, cv2.LINE_AA,
        )

    cv2.addWeighted(overlay, mask_alpha, output, 1 - mask_alpha, 0, output)
    return output
