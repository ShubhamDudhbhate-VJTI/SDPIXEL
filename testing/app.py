# ============================================================================
# Stage 2: VLM Document Intelligence Tester
# ============================================================================
# Install dependencies:
#   pip install streamlit PyMuPDF requests
#
# Run:
#   streamlit run app.py
# ============================================================================

import streamlit as st
import fitz  # PyMuPDF
import base64
import json
import requests
import io

# ---------------------------------------------------------------------------
# Configuration – change these as needed
# ---------------------------------------------------------------------------
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "ministral-3:14b-cloud"

# ---------------------------------------------------------------------------
# The extraction prompt sent to the VLM
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """You are an expert X-ray security translation engine. Carefully analyze the provided image of the cargo invoice. Extract the specified fields from the visual layout into a valid JSON object. 
For each item found in the table, you must do two things:
1. Keep 'item_name' exactly as it appears on the invoice.
2. Generate ONE 'vision_label'. This label translates the item into a physical, structural description for a downstream open-vocabulary vision model.

**CRITICAL RULES FOR 'vision_label':**
- **Mandatory Prefix:** Every vision_label MUST begin exactly with the phrase 'xray image of '.
- **No Single Words:** Never use basic nouns.
- **Focus on Structure:** Describe global geometry, silhouettes, and structural density (e.g., 'xray image of dense folded organic fabric silhouette').
- **STRICTLY NO COLORS:** The images are grayscale. Never use words like blue, red, dark, or light.

**Expected JSON Schema Output:**
{
  "parties": {
    "exporter": { "name": "string", "country": "string" },
    "consignee": { "name": "string", "country": "string" }
  },
  "shipment_details": {
    "subtotal": "number"
  },
  "extracted_items": [
    {
      "packages": "number",
      "units": "number",
      "net_weight": "string",
      "uom": "string",
      "item_name": "string", 
      "hs_code": "string",
      "origin_country": "string",
      "unit_value": "number",
      "total_value": "number",
      "vision_label": "string" 
    }
  ]
}"""


# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------

def process_pdf_to_base64(uploaded_file) -> tuple[str, bytes]:
    """
    Reads a Streamlit UploadedFile (PDF), renders the first page as a JPEG
    via PyMuPDF, and returns (base64_string, raw_jpeg_bytes).
    """
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)  # first page

    # Render at 2× zoom for clarity
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    jpeg_bytes = pix.tobytes(output="jpeg", jpg_quality=90)
    doc.close()

    b64_string = base64.b64encode(jpeg_bytes).decode("utf-8")
    return b64_string, jpeg_bytes


def extract_data_with_ollama(base64_image: str) -> dict:
    """
    Sends the base64-encoded image to the Ollama vision model and returns
    the parsed JSON response.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": EXTRACTION_PROMPT,
        "images": [base64_image],
        "stream": False,
        "format": "json",
    }

    response = requests.post(OLLAMA_API_URL, json=payload, timeout=300)
    response.raise_for_status()

    result = response.json()
    raw_text = result.get("response", "{}")

    # Attempt to parse the model output as JSON
    try:
        extracted = json.loads(raw_text)
    except json.JSONDecodeError:
        extracted = {"_raw_response": raw_text, "_error": "Model output was not valid JSON."}

    return extracted


# ---------------------------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------------------------

def main():
    # ── Page config ──────────────────────────────────────────────────────
    st.set_page_config(
        page_title="Stage 2 · VLM Document Intelligence",
        page_icon="🔬",
        layout="wide",
    )

    # ── Custom CSS ───────────────────────────────────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global */
    html, body, .stApp {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background: linear-gradient(160deg, #0f0c29 0%, #1a1a2e 40%, #16213e 100%);
    }

    /* Header banner */
    .hero-banner {
        background: linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(139,92,246,0.12) 50%, rgba(236,72,153,0.1) 100%);
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 16px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.8rem;
        backdrop-filter: blur(12px);
    }
    .hero-banner h1 {
        font-size: 1.85rem;
        font-weight: 700;
        background: linear-gradient(90deg, #818cf8, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 0.3rem 0;
    }
    .hero-banner p {
        color: #94a3b8;
        font-size: 0.95rem;
        margin: 0;
    }

    /* Cards / panels */
    .glass-card {
        background: rgba(30, 30, 60, 0.55);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 14px;
        padding: 1.5rem;
        backdrop-filter: blur(10px);
    }
    .glass-card h3 {
        color: #c4b5fd;
        font-size: 1.05rem;
        font-weight: 600;
        margin: 0 0 1rem 0;
    }

    /* Status chips */
    .status-chip {
        display: inline-block;
        padding: 0.3rem 0.85rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.03em;
    }
    .status-ready {
        background: rgba(52,211,153,0.15);
        color: #6ee7b7;
        border: 1px solid rgba(52,211,153,0.3);
    }
    .status-waiting {
        background: rgba(251,191,36,0.12);
        color: #fbbf24;
        border: 1px solid rgba(251,191,36,0.25);
    }
    .status-error {
        background: rgba(248,113,113,0.12);
        color: #f87171;
        border: 1px solid rgba(248,113,113,0.25);
    }

    /* JSON output */
    .stJson {
        border-radius: 10px !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: rgba(15, 12, 41, 0.95);
        border-right: 1px solid rgba(99,102,241,0.15);
    }
    section[data-testid="stSidebar"] .stMarkdown h2 {
        color: #a5b4fc;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li {
        color: #94a3b8;
        font-size: 0.88rem;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        border: 2px dashed rgba(99,102,241,0.35) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        transition: border-color 0.3s ease;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(139,92,246,0.6) !important;
    }

    /* Primary button */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: #fff;
        border: none;
        border-radius: 10px;
        padding: 0.65rem 1.8rem;
        font-weight: 600;
        font-size: 0.92rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(99,102,241,0.3);
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(99,102,241,0.45);
    }
    .stButton > button:active {
        transform: translateY(0);
    }

    /* Config table */
    .config-table {
        width: 100%;
        font-size: 0.85rem;
    }
    .config-table td {
        padding: 0.35rem 0;
        color: #cbd5e1;
    }
    .config-table td:first-child {
        color: #818cf8;
        font-weight: 500;
        width: 35%;
    }
    .config-table code {
        background: rgba(99,102,241,0.12);
        padding: 0.15rem 0.45rem;
        border-radius: 5px;
        color: #e2e8f0;
        font-size: 0.82rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Sidebar ──────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        st.markdown(f"""
        <table class="config-table">
            <tr><td>API Endpoint</td><td><code>{OLLAMA_API_URL}</code></td></tr>
            <tr><td>Model</td><td><code>{OLLAMA_MODEL}</code></td></tr>
            <tr><td>Output Format</td><td><code>JSON (strict)</code></td></tr>
        </table>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("## 📤 Upload Invoice")
        uploaded_file = st.file_uploader(
            "Choose a PDF invoice",
            type=["pdf"],
            help="Upload a single-page or multi-page PDF. Only the first page is processed.",
        )

        st.markdown("---")
        st.markdown("## 📋 Pipeline")
        st.markdown("""
        1. **PDF → Image** — PyMuPDF renders page 1 as JPEG  
        2. **Image → base64** — encoded for API transport  
        3. **VLM Extraction** — Ollama vision model parses fields  
        4. **JSON Output** — structured data displayed  
        """)

    # ── Hero banner ──────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-banner">
        <h1>🔬 Stage 2: VLM Document Intelligence Tester</h1>
        <p>Upload a cargo invoice PDF · Extract structured data via Vision-Language Model · Verify output</p>
    </div>
    """, unsafe_allow_html=True)

    # ── No file uploaded yet ─────────────────────────────────────────────
    if uploaded_file is None:
        st.markdown("""
        <div class="glass-card" style="text-align:center; padding:3rem 2rem;">
            <h3 style="font-size:1.2rem; margin-bottom:0.6rem;">📄 No document uploaded</h3>
            <p style="color:#94a3b8; margin:0;">Use the sidebar to upload a PDF invoice and begin extraction.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Process uploaded PDF ─────────────────────────────────────────────
    with st.spinner("Converting PDF to image…"):
        try:
            b64_image, jpeg_bytes = process_pdf_to_base64(uploaded_file)
        except Exception as exc:
            st.error(f"❌ PDF conversion failed: {exc}")
            return

    st.markdown('<span class="status-chip status-ready">✓ PDF converted</span>', unsafe_allow_html=True)

    # ── Two-column layout ────────────────────────────────────────────────
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown('<div class="glass-card"><h3>📄 Invoice Preview</h3></div>', unsafe_allow_html=True)
        st.image(jpeg_bytes, use_container_width=True, caption=f"{uploaded_file.name} — Page 1")

    with col_right:
        st.markdown('<div class="glass-card"><h3>🧠 Extraction Output</h3></div>', unsafe_allow_html=True)

        run_btn = st.button("🚀 Run Extraction", use_container_width=True)

        if run_btn:
            with st.spinner("Sending image to Ollama vision model — this may take a minute…"):
                try:
                    result = extract_data_with_ollama(b64_image)
                    st.markdown(
                        '<span class="status-chip status-ready">✓ Extraction complete</span>',
                        unsafe_allow_html=True,
                    )
                    st.json(result, expanded=True)
                except requests.exceptions.ConnectionError:
                    st.markdown(
                        '<span class="status-chip status-error">✗ Connection failed</span>',
                        unsafe_allow_html=True,
                    )
                    st.error(
                        f"Could not connect to Ollama at `{OLLAMA_API_URL}`. "
                        "Make sure `ollama serve` is running."
                    )
                except requests.exceptions.Timeout:
                    st.markdown(
                        '<span class="status-chip status-error">✗ Timeout</span>',
                        unsafe_allow_html=True,
                    )
                    st.error("The request timed out (300 s). Try a smaller document or check the model.")
                except Exception as exc:
                    st.markdown(
                        '<span class="status-chip status-error">✗ Error</span>',
                        unsafe_allow_html=True,
                    )
                    st.error(f"Extraction failed: {exc}")
        else:
            st.markdown("""
            <div style="
                border: 1px dashed rgba(99,102,241,0.25);
                border-radius: 10px;
                padding: 2rem;
                text-align: center;
                color: #64748b;
                margin-top: 0.5rem;
            ">
                <p style="font-size: 1.5rem; margin: 0 0 0.4rem 0;">⬆️</p>
                <p style="margin:0;">Click <strong>Run Extraction</strong> to send the image to the VLM.</p>
            </div>
            """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
