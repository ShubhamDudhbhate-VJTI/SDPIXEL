# Pixel — Customs X-ray Intelligence Platform
## Project Handoff Document
*Generated: 2026-04-05*

---

## 1. Repository Layout

```
Pixel/
├── Frontend/               React + Vite frontend
├── Model_Backend/          FastAPI backend + ML pipeline
├── PIDray-main/            External dataset/reference (unused at runtime)
├── cargoxray-master/       External dataset/reference (unused at runtime)
├── testing/                Ad-hoc test scripts
├── xray_v14/               Legacy model experiment directory
└── README.md               Top-level project overview
```

---

## 2. Full File Inventory

### Model_Backend/

| File | Purpose |
|------|---------|
| `main.py` | FastAPI server; full analysis pipeline wired end-to-end |
| `requirements.txt` | Python dependencies |
| `textual_risk_analyzer.py` | 13-stage deterministic data-risk engine; consumes VLM output |
| `client.py` | Manual test client for hitting the API |
| `demo_scenarios.py` | Three canned demo cases (CLEAR / SUSPICIOUS / PROHIBITED) |
| `test_vlm_sanitizer.py` | Unit tests for JSON sanitization in `vlm_extractor` |
| `PIPELINE_DOCS.md` | Integration notes for VLM + textual risk stages |
| `SHAP_Integration.md` | Notes on SHAP explainability setup |
| `model/best.pt` | Trained YOLOv8 weights for X-ray object detection |

#### Model_Backend/utils/

| File | Purpose |
|------|---------|
| `__init__.py` | Package init; re-exports `pdf_extractor`, `vlm_extractor` |
| `detector.py` | `XRayDetector` — wraps YOLOv8, returns `[{label, confidence, bbox}]` |
| `gradcam.py` | `generate_gradcam()` — pseudo Grad-CAM heatmap; `overlay_heatmap()` blender |
| `image_comparator.py` | `compare_scans()` — SSIM diff between current and reference X-ray; returns `ComparisonResult` |
| `risk_scorer.py` | `calculate_risk()` — legacy CLEAR / SUSPICIOUS / PROHIBITED scorer |
| `risk_tables.py` | Lookup tables: `CATEGORY_TABLE`, `HS_RISK_TABLE`, `COUNTRY_RISK_TABLE`, `CATEGORY_HS_GROUP` |
| `data_risk.py` | `compute_data_risk()` — value-anomaly + HS-code + country risk from invoice items |
| `visual_risk.py` | `compute_visual_risk()` + `ssim_score_to_risk()` — combines detection + SSIM + SHAP |
| `final_risk.py` | `compute_final_risk()` — blends data+visual risk → score + RED/YELLOW/GREEN |
| `zero_shot_inspector.py` | `ZeroShotManifestInspector` — OWL-ViT v2 + SAM 2; matches manifest labels to image |
| `vlm_extractor.py` | `extract_invoice_data()` — sends PDF page (base64) to Ollama VLM; returns structured invoice JSON |
| `pdf_extractor.py` | `pdf_to_base64()` / PDF→JPEG bytes helpers using PyMuPDF (separate from main.py helper) |
| `audit.py` | `AuditTrail` — logs pipeline steps to JSON; saves to `audit_logs/` |
| `encryption.py` | Fernet symmetric encryption for audit payloads before IPFS upload |
| `ipfs_client.py` | `upload_to_ipfs()` / `fetch_from_ipfs()` — Pinata IPFS upload/retrieval |
| `supabase_client.py` | `store_audit_metadata()` / `query_audits()` — Supabase audit index |
| `shap_explainer.py` | `YOLOShapExplainer` — local SHAP analysis; **contains Colab-specific code that crashes on import outside Colab** |
| `app.py` | Legacy Flask dev app (superseded by `main.py`) |
| `PackingListExtractor (1).jsx` | Orphaned React file accidentally placed in utils/ — safe to delete |

#### Model_Backend/tests/

| File | Purpose |
|------|---------|
| `__init__.py` | Test package init |
| `test_risk_tables.py` | Unit tests for all three risk lookup tables |
| `test_visual_risk.py` | Unit tests for `compute_visual_risk` + `ssim_score_to_risk` |
| `test_data_risk.py` | Unit tests for `compute_data_risk` (value anomaly, HS, country) |
| `test_final_risk.py` | Unit tests for `compute_final_risk` + RED/YELLOW/GREEN thresholds |

All 105 tests pass. Run with: `pytest tests/ -v`

#### Model_Backend/test_images/

Six sample X-ray images (CLEAR / SUSPICIOUS / PROHIBITED, JPG + PNG each) for manual testing.

---

### Frontend/

| File | Purpose |
|------|---------|
| `index.html` | Root HTML entry point |
| `vite.config.js` | Vite config; proxies `/api` → `localhost:8000` |
| `tailwind.config.js` | Tailwind with teal/cyan palette + custom animations |
| `package.json` | Node deps: React 18, Vite, Tailwind, Framer Motion, Lucide |
| `.env.example` | Template for frontend environment variables |

#### Frontend/src/

| File | Purpose |
|------|---------|
| `main.jsx` | React entry point; wraps app in `<AuthProvider>` + `<BrowserRouter>` |
| `App.jsx` | Route definitions: `/login`, `/`, `/analyze`, `/history`, `/help` |
| `index.css` | Tailwind base + global utility classes (`card`, `btn-primary`, `section-title`, etc.) |

#### Frontend/src/api/

| File | Purpose |
|------|---------|
| `analyze.js` | `analyzeScan({file, reference, manifest})` — multipart POST to `/api/analyze` |
| `manifest.js` | `extractManifest(file)` — POST to `/api/manifest/extract` |
| `assets.js` | `resolveAssetUrl(path)` — converts backend-relative paths to browser-loadable URLs |

#### Frontend/src/components/

| File | Status | Purpose |
|------|--------|---------|
| `Header.jsx` | Complete | Top nav bar |
| `Sidebar.jsx` | Complete | Left panel: manifest upload, reference image upload |
| `NavDrawer.jsx` | Complete | Slide-out nav menu with links + logout |
| `ImageUploader.jsx` | Complete | Drag-and-drop X-ray image upload |
| `AnnotatedImage.jsx` | Complete | Canvas/SVG overlay drawing YOLO bounding boxes |
| `DetectionList.jsx` | Complete | Clickable list of all detected objects |
| `RiskBadge.jsx` | Complete | CLEAR/SUSPICIOUS/PROHIBITED badge; wraps `ScoreRiskBadge` |
| `ScoreRiskBadge.jsx` | Complete | RED/YELLOW/GREEN score badge with breakdown bars |
| `GradCamHeatmap.jsx` | Complete | Side-by-side original + Grad-CAM heatmap |
| `ScanHeatmapComparison.jsx` | Complete | SSIM highlight + output heatmap comparison |
| `ManifestComparison.jsx` | Complete | Declared vs detected item matching table |
| `MetricsPanel.jsx` | Complete | Static YOLOv8 model metrics (mAP, Precision, Recall) |
| `ResultsOutputs.jsx` | Complete | Container orchestrating all output image displays |
| `ZeroShotOutput.jsx` | Complete | Zero-shot inspection verdict + item table |
| `ShapAnalysis.jsx` | Complete | SHAP explainability card (label, confidence, strength, reliability, coverage, verdict) |
| `DownloadReport.jsx` | Complete | PDF export of analysis results |
| `ProtectedRoute.jsx` | Complete | Auth guard for protected routes |

#### Frontend/src/pages/

| File | Purpose |
|------|---------|
| `LoginPage.jsx` | Auth form — any username/password accepted (localStorage only) |
| `HomePage.jsx` | Landing page with feature summary and demo link |
| `AnalyzePage.jsx` | Main page: upload → analyze → full results display |
| `HistoryPage.jsx` | Transaction lookup by ID |
| `HelpPage.jsx` | FAQ + keyboard shortcuts |

#### Frontend/src/hooks/ & utils/

| File | Purpose |
|------|---------|
| `hooks/useDetections.js` | State machine for analysis: loading/detections/risk/outputs/error; falls back to dummy data when no file is uploaded |
| `utils/constants.js` | `PROHIBITED_LABELS`, `SUSPICIOUS_LABELS`, `DUMMY_DETECTIONS`, `DUMMY_RISK`, model metrics |
| `utils/transactions.js` | `saveTransaction()` / `getTransaction()` / `listRecentTransactions()` — localStorage-backed history |

#### Frontend/src/context/ & layouts/

| File | Purpose |
|------|---------|
| `context/AuthContext.jsx` | `useAuth()` hook + `AuthProvider` — stores `{username}` in localStorage |
| `layouts/MainLayout.jsx` | Shell with `<Header>`, `<NavDrawer>`, `<Outlet>` |

---

## 3. Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| YOLOv8 X-ray detection | **Complete** | `utils/detector.py`; model at `model/best.pt` |
| Legacy risk scoring (CLEAR/SUSPICIOUS/PROHIBITED) | **Complete** | `utils/risk_scorer.py` |
| Grad-CAM heatmap | **Complete** | `utils/gradcam.py` |
| SSIM scan comparison | **Complete** | `utils/image_comparator.py`; requires reference upload |
| Zero-shot manifest inspection (OWL-ViT v2 + SAM 2) | **Complete** | `utils/zero_shot_inspector.py`; toggle with `ENABLE_ZERO_SHOT` |
| Visual risk scoring (RED/YELLOW/GREEN) | **Complete** | `utils/visual_risk.py` + `utils/final_risk.py` |
| VLM invoice extraction | **Complete** | `utils/vlm_extractor.py` → Ollama; wired in `main.py` |
| Textual risk analysis (data risk) | **Complete** | `textual_risk_analyzer.py`; wired in `main.py` |
| External SHAP service | **Complete** | `_call_shap_service()` in `main.py`; reads `SHAP_SERVICE_URL` env var |
| Local SHAP fallback | **Complete** | Falls back to `_extract_shap_intensity()` when external service unavailable |
| IPFS audit upload | **Complete** | Async background task via Pinata |
| Supabase audit index | **Complete** | `utils/supabase_client.py` |
| Audit log encryption | **Complete** | `utils/encryption.py` (Fernet) |
| Audit REST endpoints | **Complete** | `GET /api/audit/logs`, `GET /api/audit/logs/{request_id}` |
| Frontend: auth | **Complete** | localStorage; any credentials accepted (no server validation) |
| Frontend: analysis page | **Complete** | Full pipeline display including SHAP |
| Frontend: SHAP display | **Complete** | `ShapAnalysis.jsx`; only renders when `outputs.shap` is present |
| Frontend: ScoreRiskBadge | **Complete** | RED/YELLOW/GREEN with breakdown bars |
| Frontend: transaction history | **Complete** | localStorage; lookup by ID |
| Frontend: PDF report download | **Complete** | `DownloadReport.jsx` |
| Real server-side authentication | **Pending** | Currently any login is accepted |
| Audit log viewer UI | **Pending** | API exists; no frontend page built |

---

## 4. API Endpoints

### `POST /api/analyze`

**Request** — `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | image file | Yes | X-ray scan (JPEG/PNG) |
| `reference` | image file | No | Reference scan for SSIM comparison |
| `manifest` | PDF file | No | Invoice/packing-list PDF for VLM extraction + zero-shot |

**Response** — `application/json`

```json
{
  "detections": [
    {
      "id": 1,
      "label": "gun",
      "confidence": 0.9321,
      "category": "prohibited",
      "bbox": { "x": 120.5, "y": 80.3, "width": 45.2, "height": 22.1 }
    }
  ],
  "risk": {
    "level": "PROHIBITED",
    "score": 0.95,
    "reason": "Prohibited item detected",
    "data_risk": 0.61,
    "visual_risk": 0.8,
    "final_risk": 0.724,
    "decision": "RED",
    "risk_breakdown": {
      "suspicious_score": 1.0,
      "uncertain_ratio": 0.333,
      "ssim_risk": 0.9,
      "shap_intensity_score": 0.42,
      "value_anomaly": 0.7,
      "hs_code_risk": 0.5,
      "country_risk": 0.3
    }
  },
  "outputs": {
    "gradcam": "outputs/gradcam_1712345678_abc123.png",
    "highlightHeatmap": "outputs/highlight_heatmap_1712345678_abc123.png",
    "outputHeatmap": "outputs/output_heatmap_1712345678_abc123.png",
    "ssimScore": 0.72,
    "ssimInterpretation": "Moderate difference",
    "changedRegions": 3,
    "ssimRisk": 0.5,
    "shap": {
      "label": "gun",
      "confidence": 0.93,
      "strength": "High",
      "reliability": 0.88,
      "coverage": 42.0,
      "verdict": "Suspicious"
    },
    "shapIntensityScore": 0.42,
    "zeroShot": {
      "overlayImage": "outputs/zero_shot_1712345678_abc123.png",
      "verdict": "UNDECLARED_ITEMS",
      "totalObjects": 6,
      "declaredCount": 4,
      "undeclaredCount": 2,
      "missingCount": 1,
      "missingItems": ["laptop"],
      "items": [...],
      "timings": { "detection": 1.234, "segmentation": 0.891 },
      "labelsUsed": ["xray image of laptop ...]"
    },
    "zeroShotOutputImage": "outputs/zero_shot_...",
    "zeroShotOutputText": "Verdict: UNDECLARED_ITEMS\nUndeclared: 2",
    "manifestItems": ["Laptop 14inch", "Clothing Items"],
    "vlm_result": {
      "parties": {
        "exporter": { "name": "Acme Corp", "country": "China" },
        "consignee": { "name": "Import Co", "country": "India" }
      },
      "shipment_details": {
        "ship_date": "2026-03-15",
        "invoice_no": "INV-2026-001",
        "subtotal": 12500,
        "insurance": 250,
        "freight": 800,
        "packing": 150,
        "handling": 100,
        "other": 0
      },
      "extracted_items": [
        {
          "packages": 2,
          "units": 5,
          "net_weight": "12kg",
          "uom": "pcs",
          "item_name": "Laptop 14inch",
          "hs_code": "8471.30",
          "origin_country": "China",
          "unit_value": 1200,
          "total_value": 6000,
          "vision_label": "xray image of laptop showing rectangular metallic chassis with battery and keyboard structure"
        }
      ]
    },
    "data_risk_context": {
      "origin": "China",
      "region": "East Asia",
      "declared_status": "UNDER_DECLARED",
      "declared_value": 6000,
      "total_min": 8000,
      "total_max": 15000,
      "hs_codes_used": ["8471"],
      "items": [...],
      "consistency_flags": ["value_below_expected_range"]
    }
  },
  "suspicious_flag": true,
  "request_id": "a1b2c3d4-e5f6-..."
}
```

**Notes:**
- `data_risk`, `value_anomaly`, `hs_code_risk`, `country_risk` are `null` when no manifest PDF is uploaded
- `shap` in outputs is absent when neither the external service nor local SHAP succeeded
- `vlm_result` and `data_risk_context` are absent when no manifest PDF is uploaded
- All image paths in `outputs` are relative to `Model_Backend/` — serve via `GET /api/files?path=...`

---

### `POST /api/manifest/extract`

**Request** — `multipart/form-data`

| Field | Type | Required |
|-------|------|----------|
| `file` | PDF file | Yes |

**Response**

```json
{ "items": ["Laptop 14inch", "Clothing - 3 units", "..."] }
```

---

### `GET /api/files?path=<relative-path>`

Serves any file under `Model_Backend/` by its relative path (e.g., `outputs/gradcam_xyz.png`). Used by the frontend to load generated images.

Blocks path traversal (`..` and absolute paths). Returns 404 for missing files.

---

### `GET /api/health`

```json
{
  "status": "ok",
  "model_path": "model/best.pt",
  "output_dir": "/abs/path/to/outputs",
  "zero_shot_enabled": true,
  "shap_available": false
}
```

---

### `GET /api/audit/logs`

Query params: `limit` (int, optional), `date_filter` (string `DD-MM-YYYY`, optional)

```json
{ "logs": [ { "cid": "Qm...", "request_id": "...", "status": "success", "description": "...", "created_at": "..." } ] }
```

---

### `GET /api/audit/logs/{request_id}`

Fetches the CID from Supabase, downloads the encrypted blob from IPFS, decrypts it, and returns the full pipeline audit trace.

```json
{
  "audit": {
    "request_id": "...",
    "final_status": "success",
    "steps": [
      { "service": "manifest_extraction", "status": "success", "latency": 0.12, "input_data": {}, "output_data": {} },
      { "service": "vlm_extraction", "status": "success", ... },
      { "service": "yolov8_detection", "status": "success", ... },
      { "service": "gradcam_generation", ... },
      { "service": "ssim_comparison", ... },
      { "service": "shap_explainer", ... },
      { "service": "zero_shot_inspection", ... },
      { "service": "data_risk_analysis", ... },
      { "service": "composite_risk_scoring", ... }
    ]
  },
  "metadata": { "cid": "...", "created_at": "..." }
}
```

---

## 5. Environment Variables

### Backend — `Model_Backend/.env`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MODEL_PATH` | No | `model/best.pt` | Path to YOLOv8 weights |
| `OUTPUT_DIR` | No | `outputs` | Directory for generated images |
| `ENABLE_ZERO_SHOT` | No | `1` | Set to `0` to skip OWL-ViT+SAM2 (saves startup time) |
| `SHAP_SERVICE_URL` | No | *(empty)* | Full URL of external SHAP micro-service (ngrok/deployed). Empty = disabled; falls back to local SHAP |
| `SUPABASE_URL` | **Yes** (for audit) | *(empty)* | Your Supabase project URL |
| `SUPABASE_KEY` | **Yes** (for audit) | *(empty)* | Supabase service-role key |
| `PINATA_JWT` | **Yes** (for audit) | *(empty)* | Pinata API JWT for IPFS upload |
| `PINATA_GATEWAY_URL` | No | `https://gateway.pinata.cloud/ipfs` | Pinata IPFS gateway base URL |
| `ENCRYPTION_KEY` | No | auto-generated | Fernet key for audit encryption. If unset, a key is generated each run (audit logs from previous runs cannot be decrypted) |
| `AUDIT_LOG_DIR` | No | `audit_logs/` | Local directory for audit JSON files |

**Note on Ollama:** The VLM extractor (`utils/vlm_extractor.py`) uses a hardcoded default `http://localhost:11434/api/generate` with model `qwen3-vl:235b-cloud`. These are not currently read from env vars — to override, pass `ollama_url` and `model` parameters directly to `extract_invoice_data()`.

### Frontend — `Frontend/.env`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_BASE_URL` | No | *(empty = same origin)* | Backend URL when frontend is deployed separately from backend |
| `VITE_API_PROXY_TARGET` | No | `http://localhost:8000` | Override for Vite dev server proxy target |

---

## 6. Build and Run Commands

### Backend

```bash
cd Model_Backend

# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate        # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file (copy from template)
cp .env.example .env            # edit with your keys
# (no .env.example exists yet — create manually; see §5 above)

# 4. Run the server
uvicorn main:app --reload --port 8000

# 5. Run tests
pytest tests/ -v
```

The server starts at `http://localhost:8000`. API docs available at `http://localhost:8000/docs`.

### Frontend

```bash
cd Frontend

# 1. Install dependencies
npm install

# 2. (Optional) Create .env for non-default backend URL
cp .env.example .env
# VITE_API_BASE_URL=http://localhost:8000   # only needed if deployed separately

# 3. Start dev server
npm run dev
# → http://localhost:5173

# 4. Production build
npm run build
# Output in Frontend/dist/
```

### Running both together (dev)

In two separate terminals:
```bash
# Terminal 1 — backend
cd Model_Backend && uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd Frontend && npm run dev
```

Vite proxies all `/api` requests to `localhost:8000` automatically.

---

## 7. Changes Made This Session

All changes are in `Model_Backend/main.py`, `Model_Backend/requirements.txt`, and `Frontend/src/pages/AnalyzePage.jsx`.

### `Model_Backend/main.py`

**New imports added:**
- `import base64` (stdlib)
- `import fitz` (PyMuPDF) — guarded with try/except; sets `PYMUPDF_AVAILABLE`
- `import httpx` — guarded with try/except; sets `HTTPX_AVAILABLE`
- `from utils.vlm_extractor import extract_invoice_data` — guarded; sets `VLM_AVAILABLE`
- `from textual_risk_analyzer import TextualRiskAnalyzer` — guarded; sets `TEXTUAL_RISK_AVAILABLE`

**New config constant:**
- `SHAP_SERVICE_URL = os.environ.get("SHAP_SERVICE_URL", "")` — empty string = disabled

**New helper functions:**
- `pdf_to_base64(pdf_bytes: bytes) -> Optional[str]` — renders page 0 at 2× scale using PyMuPDF, returns base64 PNG string (no data-URI prefix). Returns `None` if PyMuPDF unavailable or rendering fails.
- `async _call_shap_service(image, timeout=15.0) -> Optional[dict]` — POSTs image to external SHAP service via httpx multipart upload. Returns JSON dict or `None` on any failure.

**`/api/analyze` endpoint changes:**

1. *Manifest block extended* — after pdfplumber extraction, if a manifest PDF was uploaded and VLM is available: converts PDF bytes → base64 via `pdf_to_base64()`, calls `extract_invoice_data()` via `asyncio.to_thread()`, extracts `vision_labels` list from `extracted_items[].vision_label`. Logs `"vlm_extraction"` audit step.

2. *Zero-shot label priority* — `zs_labels` now uses `vision_labels → manifest_items → DEFAULT_SCAN_LABELS` (was `manifest_items → DEFAULT_SCAN_LABELS`).

3. *Stage 3c replaced* — external SHAP service is now primary: calls `_call_shap_service(image)`, stores full dict in `outputs["shap"]`, derives `shap_intensity_score` from `coverage / 100`. If service is not configured or fails, falls back to existing local `_extract_shap_intensity()`.

4. *Data risk wired* — replaced `data_risk: Optional[float] = None` stub with `TextualRiskAnalyzer().analyze(vlm_result)` call via `asyncio.to_thread()`. Extracts `Data_Risk`, `breakdown`, and `context`. Logs `"data_risk_analysis"` audit step.

5. *`risk_breakdown` updated* — `value_anomaly`, `hs_code_risk`, `country_risk` now populated from `TextualRiskAnalyzer` breakdown (previously hardcoded `None`).

6. *New output fields* — `outputs["vlm_result"]` (full VLM structured output) and `outputs["data_risk_context"]` (risk context from `TextualRiskAnalyzer`) added when manifest is present and VLM succeeds.

### `Model_Backend/requirements.txt`

Added two new dependencies:
```
pymupdf>=1.24.0
httpx>=0.27.0
```

### `Frontend/src/pages/AnalyzePage.jsx`

- Re-added `import ShapAnalysis from '../components/ShapAnalysis'`
- Re-added render block below `<GradCamHeatmap>`:
  ```jsx
  {outputs?.shap && (
    <ShapAnalysis shap={outputs.shap} />
  )}
  ```

### Previously completed (prior sessions)

- `utils/risk_tables.py` — created with 105 lookup entries
- `utils/visual_risk.py` — created
- `utils/data_risk.py` — created
- `utils/final_risk.py` — created
- `tests/test_*.py` — 105 unit tests (all passing)
- `main.py` — `asyncio.gather` parallelism for YOLO+SSIM; `suspicious_flag`; `risk.update()` with composite fields
- `Frontend/src/components/ScoreRiskBadge.jsx` — created
- `Frontend/src/components/RiskBadge.jsx` — extended to include `ScoreRiskBadge`
- `Frontend/src/components/ShapAnalysis.jsx` — created
- `Frontend/src/pages/AnalyzePage.jsx` — Stage 9 conditional: `ZeroShotOutput` hidden when `suspicious_flag` is true

---

## 8. Pending Work

### Audit system — Supabase `date_filter` query

The `GET /api/audit/logs?date_filter=DD-MM-YYYY` endpoint converts the date string and passes it to `query_audits(date_filter=...)`, but the actual Supabase query filtering logic in `utils/supabase_client.py` may not implement the `date_filter` parameter. This needs to be verified and completed.

**What to check:**
1. Open `utils/supabase_client.py` and find the `query_audits()` function
2. Confirm it applies a `.gte()`/`.lte()` or `.eq()` date filter on the `created_at` column when `date_filter` is provided
3. If not, add the filter before `.execute()`

### Other pending items

- **Real authentication** — `LoginPage.jsx` accepts any credentials. If this is production-facing, wire it to a real auth provider (Supabase Auth is already a dependency).
- **Audit log UI** — The two audit REST endpoints exist but there is no frontend page to browse them. `HistoryPage.jsx` uses localStorage transactions only.
- **Ollama env config** — `DEFAULT_OLLAMA_URL` and `DEFAULT_MODEL` in `utils/vlm_extractor.py` are hardcoded. Consider reading from env vars for deployment flexibility.
- **`PackingListExtractor (1).jsx`** — Orphaned React file in `utils/`. Safe to delete.
- **`utils/app.py`** — Legacy Flask app, superseded by `main.py`. Safe to delete.

---

## 9. Known Issues and Warnings

### `utils/shap_explainer.py` — Colab-only code at module level

`shap_explainer.py` contains `files.upload()` and hardcoded `/content/drive/...` paths that execute at **import time** in Google Colab. Outside Colab these raise `NameError` / `FileNotFoundError`. This is handled in `main.py` by wrapping the import in try/except and setting `SHAP_AVAILABLE = False`. The file itself should not be modified — it runs correctly inside Colab.

**Effect:** `shap_available: false` in `/api/health` on any non-Colab deployment. The external SHAP service (`SHAP_SERVICE_URL`) is the production path; local SHAP is the Colab-only path.

### `ENCRYPTION_KEY` persistence

If `ENCRYPTION_KEY` is not set in `.env`, a new Fernet key is auto-generated on every server start. Any audit logs encrypted with a previous key cannot be decrypted after a restart. **Set a persistent `ENCRYPTION_KEY` in production.**

### Zero-shot inspector startup time

`ZeroShotManifestInspector` loads OWL-ViT v2 and SAM 2 weights at first use. This can take 30–90 seconds on first call depending on hardware. Set `ENABLE_ZERO_SHOT=0` in `.env` to disable during development.

### VLM extraction requires running Ollama

`extract_invoice_data()` calls `http://localhost:11434/api/generate` synchronously. If Ollama is not running or the model `qwen3-vl:235b-cloud` is not pulled, the VLM step will raise `requests.exceptions.ConnectionError`. This is caught in `main.py` and logged as a failed audit step — the pipeline continues with `vlm_result = None` (data risk will be `null`).

Pull the model with: `ollama pull qwen3-vl:235b-cloud`

### SHAP service URL is ephemeral (ngrok)

`SHAP_SERVICE_URL` points to a ngrok tunnel that changes on every Colab session restart. Update `.env` with the new URL after each Colab restart.

### Float precision in tests

`compute_visual_risk(1.0, 1.0, 1.0, 1.0)` returns `0.9999999999999999` (IEEE 754). Tests use `pytest.approx()` to handle this. Do not change assertions back to `== 1.0`.

### `outputs/` directory grows unbounded

Every analysis writes 3–5 image files to `outputs/`. There is no cleanup job. Add a cron or TTL-based cleanup for production deployments.

---

## 10. Architecture Diagram (text)

```
Browser (React/Vite)
        │
        │  POST /api/analyze (multipart)
        ▼
FastAPI (main.py)
        │
        ├─► [if manifest PDF]
        │     ├─ pdfplumber → manifest_items (text heuristic)
        │     └─ PyMuPDF → base64 → Ollama VLM → vlm_result
        │                                    └─ vision_labels
        │
        ├─► asyncio.gather (parallel)
        │     ├─ YOLOv8 detect → raw_detections
        │     └─ SSIM compare  → ssim_result (if reference uploaded)
        │
        ├─► Grad-CAM heatmap
        │
        ├─► SHAP (external service → local fallback)
        │
        ├─► Zero-shot inspector (OWL-ViT v2 + SAM 2)
        │     └─ uses vision_labels > manifest_items > DEFAULT_SCAN_LABELS
        │
        ├─► Visual risk (suspicious_score + uncertain_ratio + ssim_risk + shap)
        │
        ├─► [if vlm_result] TextualRiskAnalyzer → data_risk + breakdown
        │
        ├─► Final risk = 0.4*data_risk + 0.6*visual_risk → RED/YELLOW/GREEN
        │
        └─► AuditTrail → encrypt → IPFS (Pinata) + Supabase index (background)

Response → { detections, risk, outputs, suspicious_flag, request_id }
```
