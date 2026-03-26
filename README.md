# CargoGuard - Customs X-ray Intelligence Platform

CargoGuard is an AI-powered cargo screening platform that combines a modern React dashboard with a FastAPI inference backend to analyze customs X-ray scans.

It supports:
- Object detection on X-ray scans (YOLOv8)
- Risk scoring for suspicious/prohibited findings
- Grad-CAM style visual heatmaps
- Optional scan-vs-reference SSIM comparison
- Manifest PDF extraction and zero-shot declaration matching

## Project Structure

```text
CargoGuard/
|- Frontend/                 # React + Vite web app
|  |- src/
|  |- package.json
|
|- Model_Backend/            # FastAPI + ML inference services
|  |- main.py                # API server entrypoint
|  |- requirements.txt
|  |- utils/
|     |- detector.py
|     |- gradcam.py
|     |- image_comparator.py
|     |- risk_scorer.py
|     |- zero_shot_inspector.py
```

## Tech Stack

- Frontend: React, Vite, Tailwind CSS, Framer Motion
- Backend: FastAPI, Uvicorn
- ML/CV: Ultralytics YOLOv8, PyTorch, OpenCV, Transformers
- Document processing: pdfplumber

## Key Features

- **End-to-end analysis pipeline** via `POST /api/analyze`
- **Manifest intelligence** via `POST /api/manifest/extract`
- **Result assets serving** via `GET /api/files?path=...`
- **Operational health endpoint** via `GET /api/health`
- **Proxy-ready dev setup** (`Frontend` proxies `/api` to backend on `localhost:8000`)

## Prerequisites

- Python 3.10+ (recommended)
- Node.js 18+ and npm
- macOS/Linux/Windows with enough RAM/VRAM for model loading

## Environment Variables

Backend (`Model_Backend/main.py`) supports:

- `MODEL_PATH` (default: `model/best.pt`)
- `OUTPUT_DIR` (default: `outputs`)
- `ENABLE_ZERO_SHOT` (default: `1`; set `0` to disable heavy zero-shot loading)

Frontend supports:

- `VITE_API_BASE_URL` (optional; if unset, relative `/api` is used)
- `VITE_API_PROXY_TARGET` (optional; Vite proxy target in local dev)

## Setup and Run

### 1) Clone and enter project

```bash
git clone https://github.com/AishVerse/CargoGuard.git
cd CargoGuard
```

### 2) Backend setup

```bash
cd Model_Backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Place your trained YOLO model at:

```text
Model_Backend/model/best.pt
```

Start backend:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3) Frontend setup

Open a second terminal:

```bash
cd CargoGuard/Frontend
npm install
npm run dev
```

Frontend dev URL is typically:

```text
http://localhost:5173
```

## API Overview

### `POST /api/analyze`

Multipart form:
- `file` (required image)
- `reference` (optional image)
- `manifest` (optional PDF)

Returns:
- `detections`
- `risk`
- `outputs` (gradcam, heatmaps, zero-shot details, extracted manifest items, etc.)

### `POST /api/manifest/extract`

Uploads a PDF manifest and returns extracted item names.

### `GET /api/files?path=...`

Serves generated output files from allowed backend output paths.

### `GET /api/health`

Health and runtime configuration status.

## Typical Workflow

1. Upload a cargo X-ray image in the frontend.
2. Optionally upload:
   - a reference scan (for SSIM difference visualization),
   - a manifest PDF (for extraction + zero-shot comparison).
3. Run analysis.
4. Review:
   - annotated detections,
   - risk badge and confidence,
   - Grad-CAM and comparison heatmaps,
   - zero-shot declared vs undeclared verdict.

## Troubleshooting

- **`403` on git push**  
  Remove token from remote URL, reset credential cache, and re-authenticate GitHub.

- **Model not found (`best.pt`)**  
  Ensure file exists at `Model_Backend/model/best.pt` or set `MODEL_PATH`.

- **Frontend cannot hit backend**  
  Confirm backend runs on `localhost:8000` and Vite proxy is active.

- **Slow startup or OOM with zero-shot**  
  Set `ENABLE_ZERO_SHOT=0` to run lighter pipeline first.

- **`/api/manifest/extract` returns empty list**  
  PDF may be image-only or text extraction quality may be low; test with text-based PDFs.

## Developer Notes

- `Frontend/src/api/analyze.js` builds the multipart request contract for backend APIs.
- `Frontend/src/api/assets.js` resolves backend output paths to browser-safe URLs.
- Backend output files are written under `OUTPUT_DIR` and served with `/api/files`.

## License

No explicit license file is currently included. Add a `LICENSE` file if you plan to distribute this project publicly.
