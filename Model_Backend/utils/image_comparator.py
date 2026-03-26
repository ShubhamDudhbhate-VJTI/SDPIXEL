"""
image_comparator.py — SSIM-based image comparison for cargo X-ray scans.

Compares a current scan against a reference scan to detect meaningful
differences (added, removed, or altered objects).

Pipeline:
  1. Preprocess  — grayscale, resize, normalize, blur
  2. Align       — OpenCV ECC alignment to correct shifts/rotations
  3. SSIM        — structural similarity score + difference map
  4. Threshold   — isolate significant changes
  5. Contours    — detect and draw bounding boxes on changed regions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

logger = logging.getLogger(__name__)


# ── Data classes ────────────────────────────────────────────────────────


@dataclass
class ChangedRegion:
    """A rectangular region where differences were detected."""
    x: int
    y: int
    width: int
    height: int


@dataclass
class ComparisonResult:
    """Output of the image comparison pipeline."""
    ssim_score: float                         # 0.0 – 1.0
    changed_regions: List[ChangedRegion]      # bounding boxes of differences
    ssim_heatmap: np.ndarray                  # raw SSIM diff map  (H×W, uint8)
    highlighted_image: np.ndarray             # current scan with boxes (H×W×3, BGR)
    interpretation: str                       # "similar" / "different"


# ── Configuration ───────────────────────────────────────────────────────

TARGET_SIZE = (800, 640)        # (width, height) for consistent comparison
BLUR_KERNEL = (5, 5)            # Gaussian blur to reduce noise
DIFF_THRESHOLD = 30             # threshold to binarize the difference map
MIN_CONTOUR_AREA = 500          # ignore contours smaller than this (noise)
SSIM_SIMILAR_THRESHOLD = 0.85   # above this → "similar"


# ── Pipeline functions ──────────────────────────────────────────────────


def _preprocess(img: np.ndarray) -> np.ndarray:
    """Convert to grayscale, resize, normalize intensity, and blur."""
    # Grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # Resize to standard dimensions
    gray = cv2.resize(gray, TARGET_SIZE, interpolation=cv2.INTER_AREA)

    # Normalize intensity (histogram equalization)
    gray = cv2.equalizeHist(gray)

    # Gaussian blur to reduce noise
    gray = cv2.GaussianBlur(gray, BLUR_KERNEL, 0)

    return gray


def _align_images(current: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """
    Align reference image to current using ECC (Enhanced Correlation Coefficient).
    Returns the warped reference image.
    """
    try:
        warp_mode = cv2.MOTION_TRANSLATION
        warp_matrix = np.eye(2, 3, dtype=np.float32)

        criteria = (
            cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
            200,    # max iterations
            1e-6,   # epsilon
        )

        _, warp_matrix = cv2.findTransformECC(
            current, reference, warp_matrix, warp_mode, criteria
        )

        h, w = current.shape
        aligned = cv2.warpAffine(
            reference, warp_matrix, (w, h),
            flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP,
        )
        return aligned

    except cv2.error as exc:
        logger.warning("ECC alignment failed, using unaligned reference: %s", exc)
        return reference


def _compute_ssim(current: np.ndarray, reference: np.ndarray) -> Tuple[float, np.ndarray]:
    """
    Compute SSIM between two grayscale images of the same size.
    Returns (score, difference_map_uint8).
    """
    score, diff_map = ssim(current, reference, full=True)

    # diff_map is float64 in [0, 1]. Invert: areas that differ → higher values.
    diff_inv = (1.0 - diff_map) * 255
    diff_uint8 = np.clip(diff_inv, 0, 255).astype(np.uint8)

    return float(score), diff_uint8


def _find_changed_regions(diff_map: np.ndarray) -> List[ChangedRegion]:
    """Threshold the difference map and find contour bounding boxes."""
    _, thresh = cv2.threshold(diff_map, DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)

    # Morphological operations to clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    thresh = cv2.dilate(thresh, kernel, iterations=2)
    thresh = cv2.erode(thresh, kernel, iterations=1)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_CONTOUR_AREA:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        regions.append(ChangedRegion(x=x, y=y, width=w, height=h))

    return regions


def _draw_highlighted(
    current_color: np.ndarray,
    regions: List[ChangedRegion],
) -> np.ndarray:
    """
    Draw bounding boxes on the current scan highlighting changed regions.
    Returns a BGR image.
    """
    highlighted = current_color.copy()
    for r in regions:
        cv2.rectangle(
            highlighted,
            (r.x, r.y),
            (r.x + r.width, r.y + r.height),
            (0, 0, 255),   # Red in BGR
            2,
        )
        cv2.putText(
            highlighted,
            "Change",
            (r.x, max(r.y - 6, 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )
    return highlighted


def _colorize_heatmap(diff_map: np.ndarray) -> np.ndarray:
    """Apply JET colormap to the difference map for visualization. Returns BGR."""
    return cv2.applyColorMap(diff_map, cv2.COLORMAP_JET)


# ── Public API ──────────────────────────────────────────────────────────


def compare_scans(
    current_image: Image.Image,
    reference_image: Image.Image,
) -> ComparisonResult:
    """
    Compare current X-ray scan against a reference and return structured results.

    Parameters
    ----------
    current_image : PIL Image (RGB)
    reference_image : PIL Image (RGB)

    Returns
    -------
    ComparisonResult with SSIM score, changed regions, heatmap, and highlighted image.
    """
    # Convert PIL → OpenCV BGR
    current_bgr = cv2.cvtColor(np.array(current_image.convert("RGB")), cv2.COLOR_RGB2BGR)
    reference_bgr = cv2.cvtColor(np.array(reference_image.convert("RGB")), cv2.COLOR_RGB2BGR)

    # 1. Preprocess
    current_gray = _preprocess(current_bgr)
    reference_gray = _preprocess(reference_bgr)

    # 2. Align reference to current
    aligned_ref = _align_images(current_gray, reference_gray)

    # 3. Compute SSIM
    score, diff_map = _compute_ssim(current_gray, aligned_ref)

    # 4. Find changed regions
    regions = _find_changed_regions(diff_map)

    # 5. Colorize heatmap
    ssim_heatmap = _colorize_heatmap(diff_map)

    # 6. Draw highlighted regions on resized current image
    current_resized = cv2.resize(current_bgr, TARGET_SIZE, interpolation=cv2.INTER_AREA)
    highlighted = _draw_highlighted(current_resized, regions)

    # 7. Interpretation
    interpretation = "similar" if score >= SSIM_SIMILAR_THRESHOLD else "different"

    return ComparisonResult(
        ssim_score=round(score, 4),
        changed_regions=regions,
        ssim_heatmap=ssim_heatmap,
        highlighted_image=highlighted,
        interpretation=interpretation,
    )
