# ============================================================================
# Stage 2: VLM Document Intelligence + Textual Risk Pipeline
# ============================================================================
# Install dependencies:
#   pip install streamlit PyMuPDF requests
#
# Run (from the testing/ directory):
#   streamlit run app.py
# ============================================================================

import streamlit as st
import requests
import fitz  # PyMuPDF
import base64

from vlm_extractor import extract_invoice_data, DEFAULT_OLLAMA_URL, DEFAULT_MODEL
from textual_risk_analyzer import TextualRiskAnalyzer


def pdf_to_base64(pdf_bytes: bytes) -> tuple[str, bytes]:
    """Render first page of a PDF as JPEG; return (base64_str, raw_jpeg)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    jpeg = pix.tobytes(output="jpeg", jpg_quality=90)
    doc.close()
    return base64.b64encode(jpeg).decode("utf-8"), jpeg


analyzer = TextualRiskAnalyzer()


def main():
    st.set_page_config(
        page_title="Stage 2 · VLM + Risk Pipeline",
        page_icon="🔬",
        layout="wide",
    )

    # ── Sidebar ──────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.markdown(f"**API Endpoint:** `{DEFAULT_OLLAMA_URL}`")
        st.markdown(f"**Model:** `{DEFAULT_MODEL}`")
        st.markdown(f"**Output Format:** `JSON (strict)`")

        st.divider()
        st.header("📤 Upload Invoice")
        uploaded_file = st.file_uploader(
            "Choose a PDF invoice",
            type=["pdf"],
            help="Upload a single-page or multi-page PDF. Only the first page is processed.",
        )

        st.divider()
        st.header("📋 Pipeline")
        st.markdown(
            "1. **PDF → Image** — PyMuPDF renders page 1 as JPEG\n"
            "2. **Image → base64** — encoded for API transport\n"
            "3. **VLM Extraction** — Ollama vision model parses fields\n"
            "4. **Risk Analysis** — 13-stage deterministic risk engine\n"
            "5. **Results** — risk score + breakdown displayed"
        )

    # ── Main area ────────────────────────────────────────────────────────
    st.title("🔬 Stage 2: VLM + Textual Risk Pipeline")
    st.caption(
        "Upload a cargo invoice PDF · Extract structured data via VLM · "
        "Run 13-stage risk analysis · Verify output"
    )

    if uploaded_file is None:
        st.info("📄 Use the sidebar to upload a PDF invoice and begin extraction.")
        return

    # ── Process uploaded PDF ─────────────────────────────────────────────
    with st.spinner("Converting PDF to image…"):
        try:
            pdf_bytes = uploaded_file.read()
            b64_image, jpeg_bytes = pdf_to_base64(pdf_bytes)
        except Exception as exc:
            st.error(f"❌ PDF conversion failed: {exc}")
            return

    st.success("✓ PDF converted")

    # ── Two-column layout ────────────────────────────────────────────────
    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        st.subheader("📄 Invoice Preview")
        st.image(jpeg_bytes, use_container_width=True, caption=f"{uploaded_file.name} — Page 1")

    with col_right:
        st.subheader("🧠 Extraction + Risk Analysis")

        if not st.button("🚀 Run Full Pipeline", use_container_width=True):
            st.info("⬆️ Click **Run Full Pipeline** to send the image to the VLM and run risk analysis.")
            return

        # ── Step 1: VLM Extraction ───────────────────────────────────
        with st.spinner("Sending image to Ollama vision model — this may take a minute…"):
            try:
                vlm_result = extract_invoice_data(b64_image)
            except requests.exceptions.ConnectionError:
                st.error(
                    f"Could not connect to Ollama at `{DEFAULT_OLLAMA_URL}`. "
                    "Make sure `ollama serve` is running."
                )
                return
            except requests.exceptions.Timeout:
                st.error("The request timed out (300 s). Try a smaller document or check the model.")
                return
            except Exception as exc:
                st.error(f"Extraction failed: {exc}")
                return

        if "_error" in vlm_result:
            st.error(f"⚠️ VLM output could not be parsed: {vlm_result['_error']}")
            st.json(vlm_result, expanded=True)
            return

        st.success("✓ VLM extraction complete")

        # ── Step 2: Textual Risk Analysis ────────────────────────────
        with st.spinner("Running 13-stage risk analysis…"):
            risk_result = analyzer.analyze(vlm_result)
            risk_dict = risk_result.to_dict()

        st.success("✓ Risk analysis complete")

    # ── Results section (full width) ─────────────────────────────────────
    st.divider()

    risk_level = risk_dict["risk_level"]
    data_risk = risk_dict["Data_Risk"]
    level_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(risk_level, "⚪")

    st.header(f"{level_emoji} Risk Level: {risk_level}  —  Data Risk Score: {data_risk:.4f}")

    # ── Breakdown metrics ────────────────────────────────────────────────
    breakdown = risk_dict["breakdown"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Value Anomaly", f"{breakdown['value_anomaly']:.4f}")
    m2.metric("HS Code Risk", f"{breakdown['hs_code_risk']:.4f}")
    m3.metric("Importer Risk", f"{breakdown['importer_risk']:.4f}")
    m4.metric("Country Risk", f"{breakdown['country_risk']:.4f}")

    # ── Context details ──────────────────────────────────────────────────
    ctx = risk_dict["context"]
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("📦 Shipment Context")
        st.markdown(f"**Origin:** {ctx['origin']}  ({ctx['region']})")
        st.markdown(f"**Declared Value:** {ctx['declared_value']}  ({ctx['declared_status']})")
        st.markdown(f"**Expected Range:** [{ctx['total_min']}, {ctx['total_max']}]")
        st.markdown(f"**HS Codes Used:** {', '.join(ctx['hs_codes_used'])}")

        if ctx["consistency_flags"]:
            st.warning("⚠️ HS ↔ Category Mismatches")
            for flag in ctx["consistency_flags"]:
                st.markdown(
                    f"- **{flag['item']}** → expected HS `{flag['expected_hs']}`, "
                    f"got `{flag['declared_hs']}`"
                )

    with col_b:
        st.subheader("📋 Extracted Items")
        for item in ctx["items"]:
            st.markdown(
                f"- **{item['item_name']}** — "
                f"qty: {item['quantity']}, "
                f"category: `{item['category']}`, "
                f"HS: `{item['hs_code_raw']}`"
            )

    # ── Raw JSON outputs (expandable) ────────────────────────────────────
    st.divider()

    with st.expander("📄 Raw VLM Output", expanded=False):
        st.json(vlm_result, expanded=True)

    with st.expander("📊 Full Risk Analysis Result", expanded=False):
        st.json(risk_dict, expanded=True)


if __name__ == "__main__":
    main()
