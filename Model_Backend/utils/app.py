"""
app.py — V2 Streamlit UI for Zero-Shot Cargo Manifest Inspector
================================================================
OWL-ViT v2 + SAM 2 pipeline with:
  - Dual-pass reconciliation (Sweep → Manifest)
  - Dynamic sweep strategy (tunable from UI)
  - Per-label anti-clumping detection
  - Missing-item detection
  - Live threshold tuning

Run with:  streamlit run app.py
"""

from __future__ import annotations

import tempfile
import logging
import warnings
from pathlib import Path

# Suppress harmless torch.classes instantiation warning
warnings.filterwarnings(
    "ignore",
    message=".*Tried to instantiate class.*__path__._path.*",
)

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

# ── Streamlit version compatibility ──────────────────────────────────────
# `use_container_width` was introduced in newer Streamlit.
# • st.image() — older versions accept `use_column_width` instead.
# • st.dataframe() — only has `use_container_width`; no fallback exists.
import inspect as _inspect

_img_params = _inspect.signature(st.image).parameters
_IMG_WIDE = (
    {"use_container_width": True}
    if "use_container_width" in _img_params
    else {"use_column_width": True}
)

_df_params = _inspect.signature(st.dataframe).parameters
_DF_WIDE = (
    {"use_container_width": True}
    if "use_container_width" in _df_params
    else {}
)

from zero_shot_inspector import (
    ZeroShotManifestInspector,
    InspectionResult,
    CargoVerdict,
    draw_inspection_overlay,
    ITEM_COLORS_BGR,
    DEFAULT_SWEEP_QUERIES,
    DEFAULT_BOX_THRESHOLD,
    DEFAULT_TEXT_THRESHOLD,
    DEFAULT_IOU_MATCH_THRESHOLD,
    DEFAULT_NMS_THRESHOLD,
)

# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pixel · Cargo Inspector V2",
    page_icon="🛃",
    layout="wide",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Cached model loading
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner="Loading OWL-ViT v2 + SAM 2 models …")
def get_inspector() -> ZeroShotManifestInspector:
    return ZeroShotManifestInspector()


# ═══════════════════════════════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("🛃 Inspector V2")
    st.caption("OWL-ViT v2 · Dual-Pass Detection · SAM 2")

    st.markdown("---")

    uploaded_file = st.file_uploader(
        "📤 Upload X-Ray Scan",
        type=["png", "jpg", "jpeg", "bmp", "tiff", "webp"],
    )

    st.markdown("---")
    st.subheader("📋 Manifest Declaration")
    manifest_text = st.text_area(
        "What is **declared** in the cargo?",
        placeholder="laptop, shoes, copper wire, cables",
        help="Comma-separated list of items the shipper says are inside.",
    )

    st.subheader("🔍 Sweep Strategy")
    sweep_text = st.text_area(
        "Structural terms to **find hidden items**",
        value="package, metallic mass, dense structure, wire bundle, "
              "electronic device, container, bottle, organic matter",
        help=(
            "Comma-separated domain hints for the catch-all sweep. "
            "Tune these live during your presentation if the model "
            "misses occluded items."
        ),
    )

    st.markdown("---")
    st.subheader("🎛️ Detection Thresholds")

    box_threshold = st.slider(
        "Box Confidence / Objectness",
        min_value=0.01, max_value=0.90,
        value=DEFAULT_BOX_THRESHOLD, step=0.01,
        help="How sure the model needs to be that a physical object exists.",
    )
    text_threshold = st.slider(
        "Semantic / Text Similarity",
        min_value=0.01, max_value=0.90,
        value=DEFAULT_TEXT_THRESHOLD, step=0.01,
        help="How strict the model should be when matching visual object to manifest text.",
    )
    iou_threshold = st.slider(
        "IoU Match Threshold",
        min_value=0.05, max_value=0.90,
        value=DEFAULT_IOU_MATCH_THRESHOLD, step=0.05,
        help="IoU above which a sweep detection is matched to a declared item.",
    )
    nms_threshold = st.slider(
        "NMS Overlap Threshold",
        min_value=0.10, max_value=0.90,
        value=DEFAULT_NMS_THRESHOLD, step=0.05,
        help="IoU threshold for merging overlapping bounding boxes.",
    )

    st.markdown("---")
    with st.expander("🔧 Advanced"):
        use_iterative = st.toggle(
            "Per-label detection (anti-clumping)",
            value=True,
            help="Run OWL-ViT once per manifest label to prevent label clumping.",
        )

    st.markdown("---")
    run_button = st.button(
        "🚀 Run Inspection", type="primary",
    )


# ═══════════════════════════════════════════════════════════════════════════
# Main panel
# ═══════════════════════════════════════════════════════════════════════════

st.title("🛃 Zero-Shot Cargo Manifest Inspector V2")
st.caption(
    "**Dual-pass pipeline**: Pass 1 sweeps for *all* physical objects using your custom prompts. "
    "Pass 2 verifies declared manifest items. IoU reconciliation flags undeclared & missing goods."
)

if uploaded_file is None:
    st.info("👈 Upload an X-ray image in the sidebar to begin.", icon="📤")
    st.stop()

# Save to temp
suffix = Path(uploaded_file.name).suffix
with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
    tmp.write(uploaded_file.getvalue())
    temp_path = tmp.name

original_pil = Image.open(temp_path).convert("RGB")

if not run_button:
    st.image(original_pil, caption="Uploaded scan — click **Run Inspection**.", **_IMG_WIDE)
    st.stop()

# ── Parse inputs ─────────────────────────────────────────────────────────
manifest_labels = [
    lbl.strip() for lbl in manifest_text.replace(";", ",").split(",") if lbl.strip()
]
if not manifest_labels:
    st.error("⚠️ Provide at least one manifest label (comma-separated).")
    st.stop()

sweep_queries = [
    q.strip() for q in sweep_text.replace(";", ",").split(",") if q.strip()
]
# If user left sweep empty, fall back to defaults
if not sweep_queries:
    sweep_queries = list(DEFAULT_SWEEP_QUERIES)

col_m, col_s = st.columns(2)
with col_m:
    st.info(f"**Manifest ({len(manifest_labels)}):** {', '.join(manifest_labels)}")
with col_s:
    st.info(f"**Sweep ({len(sweep_queries)}):** {', '.join(sweep_queries)}")

# ── Run pipeline ─────────────────────────────────────────────────────────
with st.spinner("Pass 1 (Sweep) → Pass 2 (Manifest) → NMS → IoU → SAM 2 …"):
    try:
        inspector = get_inspector()
        result: InspectionResult = inspector.inspect(
            image_path=temp_path,
            manifest_labels=manifest_labels,
            sweep_queries=sweep_queries,
            box_threshold=box_threshold,
            text_threshold=text_threshold,
            iou_match_threshold=iou_threshold,
            nms_threshold=nms_threshold,
            use_iterative=use_iterative,
        )
    except Exception as exc:
        st.error(f"❌ Pipeline error: {exc}")
        logger.exception("Pipeline failed")
        st.stop()

# ═══════════════════════════════════════════════════════════════════════════
# Verdict Banner
# ═══════════════════════════════════════════════════════════════════════════

if result.verdict == CargoVerdict.CLEAR:
    st.success(f"✅ **Verdict: {result.verdict.value}**", icon="✅")
elif result.verdict == CargoVerdict.UNDECLARED_ITEMS:
    st.warning(f"🚨 **Verdict: {result.verdict.value}**", icon="🚨")
elif result.verdict == CargoVerdict.MISSING_DECLARED_GOODS:
    st.error(f"🔴 **Verdict: {result.verdict.value}**", icon="🔴")
elif result.verdict == CargoVerdict.MIXED:
    st.error(f"🔴 **Verdict: {result.verdict.value}**", icon="🔴")

# Missing items callout
if result.missing_manifest_items:
    st.error(
        f"**⚠️ MISSING DECLARED ITEMS:** {', '.join(result.missing_manifest_items)}\n\n"
        "These items are listed in the manifest but were **NOT visually detected** "
        "in the X-ray scan. This may indicate cargo substitution.",
        icon="🚫",
    )

# ═══════════════════════════════════════════════════════════════════════════
# Visual Output
# ═══════════════════════════════════════════════════════════════════════════

original_bgr = cv2.cvtColor(np.array(original_pil), cv2.COLOR_RGB2BGR)
annotated_bgr = draw_inspection_overlay(original_bgr, result)
annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Original Scan")
    st.image(original_pil, **_IMG_WIDE)
with col2:
    st.subheader("Inspection Overlay")
    st.image(annotated_rgb, **_IMG_WIDE)

# ── Color Legend ─────────────────────────────────────────────────────────
if result.all_items:
    st.markdown("#### 🎨 Color Legend")
    legend_cols = st.columns(min(len(result.all_items), 6))
    for i, item in enumerate(result.all_items):
        col = legend_cols[i % len(legend_cols)]
        bgr = ITEM_COLORS_BGR[item.index % len(ITEM_COLORS_BGR)]
        hex_color = f"#{bgr[2]:02x}{bgr[1]:02x}{bgr[0]:02x}"
        status_icon = "✓" if item.status == "declared" else "⚠"
        col.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;margin:2px 0">'
            f'<div style="width:16px;height:16px;border-radius:3px;'
            f'background:{hex_color};border:1px solid #555"></div>'
            f'<span style="font-size:0.85em">[{item.index}] {item.label} {status_icon}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Metrics ──────────────────────────────────────────────────────────────
st.markdown("---")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Objects", len(result.all_items))
m2.metric("Declared ✓", len(result.declared_items_found))
m3.metric("Undeclared ⚠", len(result.undeclared_items))
m4.metric("Missing 🚫", len(result.missing_manifest_items))

# ═══════════════════════════════════════════════════════════════════════════
# Results Table
# ═══════════════════════════════════════════════════════════════════════════

st.subheader("📋 Detailed Results")
table_data = result.summary_table()

if table_data:
    df = pd.DataFrame(table_data)

    def _highlight(row):
        if row["status"] == "undeclared":
            return ["background-color: rgba(230, 50, 50, 0.15)"] * len(row)
        return ["background-color: rgba(50, 200, 50, 0.10)"] * len(row)

    styled = df.style.apply(_highlight, axis=1).format({"confidence": "{:.2%}"})
    st.dataframe(styled, **_DF_WIDE, hide_index=True)
else:
    st.info("No objects detected.")

# ── Timings ──────────────────────────────────────────────────────────────
with st.expander("⏱ Pipeline Timing Breakdown"):
    timing_df = pd.DataFrame([
        {"Stage": k.replace("_", " ").title(), "Time (s)": f"{v:.3f}"}
        for k, v in result.timings.items()
    ])
    st.dataframe(timing_df, **_DF_WIDE, hide_index=True)

# ── Raw JSON ─────────────────────────────────────────────────────────────
with st.expander("📦 Raw JSON Output"):
    st.json({
        "verdict": result.verdict.value,
        "manifest_labels": result.manifest_labels,
        "missing_manifest_items": result.missing_manifest_items,
        "sweep_queries_used": sweep_queries,
        "total_objects": len(result.all_items),
        "declared_count": len(result.declared_items_found),
        "undeclared_count": len(result.undeclared_items),
        "items": table_data,
        "timings": result.timings,
    })
