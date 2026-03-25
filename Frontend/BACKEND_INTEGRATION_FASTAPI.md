# FastAPI Backend Integration (Frontend Contract)

This Frontend is already wired for backend integration. Implement the endpoints below in **FastAPI** and the UI will work without further Frontend changes.

## Base URL / Dev proxy

- In development (`npm run dev`), the Vite server proxies **`/api/*`** to a backend target (default: `http://localhost:8000`). See `vite.config.js`.
- Optionally set `VITE_API_BASE_URL` to call a remote backend directly (see `.env.example`).

---

## 1) Analyze endpoint

### **`POST /api/analyze`**

#### Request

- **Content-Type**: `multipart/form-data`
- **Form field name**: **`file`**
- **Type**: image (`image/*`)

#### Response (JSON)

Return:
- `detections`: list
- `risk`: object
- `outputs`: object

Example:

```json
{
  "detections": [
    {
      "id": 1,
      "label": "Gun",
      "confidence": 0.85,
      "category": "prohibited",
      "bbox": { "x": 120, "y": 200, "width": 150, "height": 100 }
    }
  ],
  "risk": {
    "level": "PROHIBITED",
    "score": 85,
    "reason": "Firearms detected with high confidence."
  },
  "outputs": {
    "modelOutputImages": ["outputs/out1.png", "outputs/out2.png"],
    "objectsImage": "outputs/objects.png"
  }
}
```

#### Notes

- `outputs.modelOutputImages` may be:
  - a list of **public URLs**, OR
  - a list of **file paths** (recommended: paths under `outputs/`).
- `outputs.objectsImage` may be:
  - a **public URL**, OR
  - a **file path**.

If you return **file paths**, the Frontend will automatically load them through `GET /api/files?path=...` (next section).

---

## 2) File serving endpoint (required if outputs are file paths)

### **`GET /api/files?path=...`**

The Frontend uses this endpoint to display images when `outputs.*` contains file paths.

Example request:

```
GET /api/files?path=outputs/out1.png
```

#### Response

- Return raw file bytes with correct `Content-Type` (`image/png`, `image/jpeg`, etc.).

#### Security requirements

Implement strict path validation:
- Only allow reads from a safe output directory (e.g. `./outputs`).
- Block path traversal (`..`) and absolute paths.

---

## Minimal FastAPI skeleton (implementation reference)

```python
from pathlib import Path
import mimetypes
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()
OUTPUT_DIR = Path("outputs").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="file must be an image")

    # TODO: run ML inference, write output images under OUTPUT_DIR
    # Return paths (or URLs) as shown in the contract above.
    return {
        "detections": [],
        "risk": {"level": "CLEAR", "score": 0, "reason": "placeholder"},
        "outputs": {
            "modelOutputImages": [],
            "objectsImage": None
        }
    }

@app.get("/api/files")
def files(path: str):
    # Prevent path traversal; allow only within OUTPUT_DIR.parent
    candidate = Path(path).as_posix().lstrip("/")
    full_path = (OUTPUT_DIR.parent / candidate).resolve()

    allowed_root = OUTPUT_DIR.parent.resolve()
    if allowed_root not in full_path.parents and full_path != allowed_root:
        raise HTTPException(status_code=400, detail="invalid path")
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="file not found")

    mime, _ = mimetypes.guess_type(str(full_path))
    return FileResponse(str(full_path), media_type=mime or "application/octet-stream")
```

