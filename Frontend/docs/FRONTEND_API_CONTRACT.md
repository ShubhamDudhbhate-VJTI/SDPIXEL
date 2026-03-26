# Frontend API contract (backend reference)

This document is the **canonical** contract between the Pixel React app and the backend. The UI expects a FastAPI (or compatible) server; in development, Vite proxies `/api/*` to `VITE_API_PROXY_TARGET` or `http://localhost:8000` (see `vite.config.js`). Optional direct base URL: `VITE_API_BASE_URL` (see `.env.example`).

## UI behaviour (what the backend should support)

- **Manifest**: Users upload a PDF in the sidebar only (no manual text manifest). The app calls **`POST /api/manifest/extract`** and stores returned items for “Objects in cargo”, manifest comparison, and reports.
- **Analyze**: Users upload a scan image and run analysis. The app may also send an optional **reference** image and optional **manifest** PDF in the same request so the server can produce comparison heatmaps and aligned manifest processing.
- **Final output**: No separate “model output” image gallery. The “Objects in cargo” block is a **list** driven by manifest extract (and optionally by `outputs.manifestItems` / `outputs.manifest_items` from analyze if the server returns an authoritative list).
- **Heatmaps**: The “AI attention heatmap” card uses **`outputs.gradcam`** (or aliases below) when present; otherwise a placeholder overlay is shown. The **“Scan and heatmap comparison”** section always appears after that card and shows reference vs upload scans plus two heatmap slots from **`outputs.highlightHeatmap`** and **`outputs.outputHeatmap`** (and snake_case aliases).
- **Removed**: Gated “View output” / “Hide”, manual manifest textarea, old three-panel image comparison component.

---

## 1. `POST /api/manifest/extract`

**Purpose:** Parse a manifest PDF and return line items for the UI.

| | |
|---|---|
| **Content-Type** | `multipart/form-data` |
| **Field** | `file` — PDF (`application/pdf`) |

**Response** `200` JSON:

```json
{
  "items": ["Textiles", "Laptop batteries", "Kitchen tools"]
}
```

Aliases accepted by the client when parsing JSON: `manifest_items` (same shape as `items`).

**Errors:** Return non-2xx with a text or JSON `detail` body; the sidebar shows the error message.

---

## 2. `POST /api/analyze`

**Purpose:** Run detection / risk / auxiliary outputs on the uploaded scan.

| | |
|---|---|
| **Content-Type** | `multipart/form-data` |
| **Field** | `file` — **required** when the user runs a real analysis (image, `image/*`) |
| **Field** | `reference` — optional; reference scan image (`image/*`) |
| **Field** | `manifest` — optional; same manifest PDF as in the sidebar (`application/pdf`) |

If `file` is omitted, the frontend still runs **demo mode** locally and does not call this endpoint.

**Response** `200` JSON (core):

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
    "gradcam": "outputs/gradcam.png",
    "highlightHeatmap": "outputs/highlight.png",
    "outputHeatmap": "outputs/output_heatmap.png",
    "manifestItems": ["Optional", "server-side", "item list"]
  }
}
```

### `outputs` keys (optional unless noted)

| Key | Aliases (client accepts) | Description |
|-----|---------------------------|-------------|
| `gradcam` | `gradCamImage`, `grad_cam` | Single heatmap image URL or path served via `/api/files` |
| `highlightHeatmap` | `highlight_heatmap` | Highlighted / attention comparison image |
| `outputHeatmap` | `output_heatmap` | Second heatmap for side-by-side comparison |
| `manifestItems` | `manifest_items` | If present and non-empty, overrides sidebar-derived list in **Objects in cargo** |
| `zeroShotOutputImage` | `zeroShotOutputImages`, `zero_shot_output_image`, `zero_shot_output_images` | Zero-shot model output image(s) served via `/api/files` |
| `zeroShotOutputText` | `zero_shot_output_text` | Optional zero-shot model output text (rendered as monospaced block) |

Paths under a safe directory (e.g. `outputs/...`) should be returned as strings; the browser loads them through **`GET /api/files?path=...`**.

---

## 3. `GET /api/files?path=...`

**Purpose:** Serve files referenced by path strings in JSON responses.

**Example:** `GET /api/files?path=outputs%2Fgradcam.png`

**Response:** Raw bytes with correct `Content-Type` (`image/png`, `image/jpeg`, etc.).

**Security (required):**

- Allow reads only under a configured output (or project) root.
- Reject `..`, absolute paths, and symlink escapes.

---

## Error handling (client)

On analyze failure, the app falls back to **dummy** detections/risk for demo purposes and shows an error banner. Manifest extract has **no** dummy fallback: the user must fix the PDF or the server.

---

## Related files in the repo

- [`src/api/analyze.js`](../src/api/analyze.js) — analyze `fetch`
- [`src/api/manifest.js`](../src/api/manifest.js) — manifest extract `fetch`
- [`src/api/assets.js`](../src/api/assets.js) — path → `/api/files?path=...`

Legacy note: [`BACKEND_INTEGRATION_FASTAPI.md`](../BACKEND_INTEGRATION_FASTAPI.md) may still describe older shapes (`modelOutputImages`, `objectsImage`); this document supersedes those for the current UI.
