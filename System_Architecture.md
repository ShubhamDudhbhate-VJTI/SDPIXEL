# CargoGuard — System Architecture & Model Documentation
**Comprehensive Technical Reference for the AI-Powered Cargo X-Ray Inspection Platform**

---

## 1. System Overview

CargoGuard is an AI-powered cargo X-ray inspection platform that automates the detection of prohibited, suspicious, and undeclared items in customs shipments. The system combines **three parallel AI pipelines**, a **manifest verification algorithm**, and a **decentralized audit trail** to produce a unified risk assessment.

### Core Philosophy
- **Parallel Execution:** Three independent AI services run simultaneously for speed.
- **Multi-Model Fusion:** Final risk is derived by combining insights from all models, not relying on any single one.
- **Tamper-Proof Auditing:** Every pipeline execution is encrypted and stored on IPFS (decentralized storage) with metadata in Supabase.

---

## 2. High-Level Pipeline Architecture

```
                          ┌─────────────────────┐
                          │   User Uploads:      │
                          │  • X-ray Image       │
                          │  • Reference Scan    │
                          │  • Manifest PDF      │
                          └──────────┬───────────┘
                                     │
                          ┌──────────▼───────────┐
                          │   PRE-PROCESSING     │
                          │  • Save temp files   │
                          │  • Parse manifest    │
                          │    via PDF parser     │
                          └──────────┬───────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
    ┌─────────▼─────────┐  ┌────────▼────────┐  ┌─────────▼─────────┐
    │   PATH 1          │  │   PATH 2        │  │   PATH 3          │
    │   YOLO + GradCAM  │  │   Zero-Shot     │  │   SSIM Service    │
    │   (Detection +    │  │   (Manifest     │  │   (Scan-to-Scan   │
    │    Heatmap)        │  │    Verification)│    Comparison)  │
    └─────────┬─────────┘  └────────┬────────┘  └─────────┬─────────┘
              │                      │                      │
              │  Detections +        │  Verdict +           │  SSIM Score +
              │  Confidence Scores   │  Missing Items +     │  Changed Regions
              │  + Heatmap           │  Undeclared Items    │  + Heatmaps
              │                      │                      │
              └──────────────────────┼──────────────────────┘
                                     │
                          ┌──────────▼───────────┐
                          │   RISK AGGREGATION   │
                          │  Combines all three   │
                          │  model outputs into   │
                          │  a unified risk score │
                          │  (0-100) + level      │
                          └──────────┬───────────┘
                                     │
                     ┌───────────────┼───────────────┐
                     │               │               │
              ┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
              │  Frontend   │ │   Audit   │ │   IPFS +    │
              │  Response   │ │   Trail   │ │   Supabase  │
              │  (JSON)     │ │   (Log)   │ │   (Storage) │
              └─────────────┘ └───────────┘ └─────────────┘
```

---

## 3. Pre-Processing Stage

### 3A. Image Ingestion

| Step | Action |
|---|---|
| 1 | Validate that the uploaded file is an image (`content_type: image/*`) |
| 2 | Save the X-ray image to a temporary file on disk |
| 3 | Open with PIL and convert to RGB color space |
| 4 | If a reference scan is provided, save it as a separate temp file |

### 3B. Manifest PDF Parsing

| Step | Action |
|---|---|
| 1 | Accept an optional PDF file (invoice/manifest/packing list) |
| 2 | Use `pdfplumber` to extract raw text from every page |
| 3 | Apply heuristic filtering to separate item names from metadata: |
|   | • Skip headers like "Total", "Subtotal", "Date", "Invoice" |
|   | • Skip lines shorter than 2 chars or longer than 200 chars |
|   | • Skip purely numeric lines (quantities, codes) |
| 4 | Return a clean `list[str]` of declared cargo item names |

**Example Input (PDF text):**
```
Invoice #12345
Date: 2026-04-04
Description: Cargo Shipment

Laptop Dell XPS 15
iPhone 14 Pro
USB-C Cable Pack
Nike Running Shoes

Total: 4 items
Weight: 12.5 kg
```

**Example Output:**
```python
["Laptop Dell XPS 15", "iPhone 14 Pro", "USB-C Cable Pack", "Nike Running Shoes"]
```

These extracted labels are then fed directly into the Zero-Shot model (Path 2) as the "manifest labels" to verify against.

---

## 4. PATH 1 — YOLOv8 Object Detection + GradCAM Heatmap

### What It Does
Detects **prohibited and suspicious items** (guns, knives, bullets, hammers, etc.) in the X-ray image using a custom-trained YOLOv8 model.

### Model Details

| Property | Value |
|---|---|
| Architecture | YOLOv8 (Ultralytics) |
| Model File | `model/best.pt` (custom-trained on PIDray dataset) |
| Input | PIL Image (RGB) |
| Confidence Threshold | 0.25 |
| Output | List of bounding boxes with labels and confidence scores |

### Detection Categories

The model classifies detected objects into three threat tiers:

| Tier | Color Code | Items |
|---|---|---|
| **PROHIBITED** 🔴 | Red | Gun, Bullet, Knife |
| **SUSPICIOUS** 🟠 | Orange | Baton, Plier, Hammer, Powerbank, Scissors, Wrench, Sprayer, Handcuffs, Lighter |
| **CLEAR** 🟢 | Green | Any other detected object |

### Pipeline Steps

```
X-ray Image
    │
    ▼
┌────────────────────┐
│  YOLOv8 Inference  │
│  (conf ≥ 0.25)     │
└────────┬───────────┘
         │
         ├──► Raw Detections: [{label, confidence, bbox[x1,y1,x2,y2]}]
         │
         ▼
┌────────────────────┐
│  Detection         │
│  Transformation    │
│  • Categorize      │
│    (prohibited/    │
│     suspicious/    │
│     clear)         │
│  • Convert bbox    │
│    to {x,y,w,h}    │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  GradCAM Heatmap   │
│  Generation        │
│  • Re-run YOLO     │
│  • Accumulate      │
│    confidence per  │
│    bounding box    │
│    region          │
│  • Gaussian blur   │
│    (51x51 kernel)  │
│  • Overlay on      │
│    original (60/40 │
│    blend)          │
└────────┬───────────┘
         │
         ▼
    Heatmap Image (saved as PNG)
```

### GradCAM Visualization Logic
1. Run YOLOv8 inference again on the same image.
2. For every detected bounding box, accumulate the confidence score onto a heatmap matrix.
3. Normalize the heatmap to `[0, 1]`.
4. Apply Gaussian blur (`51×51` kernel) for smooth gradient visualization.
5. Apply JET colormap (blue → green → yellow → red).
6. Blend: `60% original image + 40% heatmap overlay`.

### Output
```json
{
  "detections": [
    {
      "id": 1,
      "label": "gun",
      "confidence": 0.94,
      "category": "prohibited",
      "bbox": {"x": 120, "y": 80, "width": 200, "height": 150}
    }
  ],
  "outputs": {
    "gradcam": "outputs/gradcam_1775304250_397f0171.png"
  }
}
```

### SHAP (SHapley Additive exPlanations) — Feature Attribution

While GradCAM answers **"WHERE is the model looking?"**, SHAP answers **"WHY did the model make this decision?"**

#### What is SHAP?
SHAP is rooted in **cooperative game theory** (Shapley values). It treats each pixel/feature of the X-ray image as a "player" in a game, and calculates how much each player (pixel region) contributed to the model's final prediction.

#### How It Works in CargoGuard

```
YOLOv8 Detection Output (e.g., "gun" at 94% confidence)
    │
    ▼
┌──────────────────────────────────┐
│  Step 1: Image Partitioning     │
│  • Divide the X-ray into a      │
│    grid of superpixels (regions) │
│    using SLIC segmentation       │
│  • Typically 50-100 segments     │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  Step 2: Perturbation           │
│  • Systematically mask/remove    │
│    combinations of superpixels   │
│  • Re-run YOLO on each masked    │
│    version of the image          │
│  • Observe how confidence drops  │
│    when each region is removed   │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  Step 3: Shapley Value Calc     │
│  • For each superpixel, compute  │
│    its marginal contribution     │
│    to the prediction across ALL  │
│    possible coalitions           │
│  • Uses kernel approximation     │
│    (exact computation is NP-hard)│
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  Step 4: Attribution Map        │
│  • Positive SHAP value → region  │
│    SUPPORTS the prediction       │
│    (e.g., barrel shape = gun)    │
│  • Negative SHAP value → region  │
│    CONTRADICTS the prediction    │
│    (e.g., organic texture ≠ gun) │
│  • Generate red/blue heatmap     │
└──────────────────────────────────┘
```

#### GradCAM vs SHAP — Complementary Roles

| Aspect | GradCAM | SHAP |
|---|---|---|
| **Question answered** | Where is the model focused? | Why did the model decide this? |
| **Technique** | Gradient-based (backpropagation) | Game theory (perturbation-based) |
| **Speed** | Very fast (~0.5s) | Slower (~5-15s per detection) |
| **Output** | Single heatmap overlay | Per-feature attribution scores |
| **Interpretation** | "The model is looking at this area" | "This region contributed +32% to the gun prediction" |
| **Use case** | Quick visual sanity check | Detailed forensic explanation for auditors |

#### Why Both Matter for Customs Auditing
- **GradCAM** gives the customs officer a quick visual: *"The AI is looking at the top-right corner."*
- **SHAP** gives the auditor a forensic explanation: *"The metallic density in region 7 contributed 42% to the 'gun' classification, while the elongated shape in region 12 contributed 28%."*

Together, they provide **full explainability** — critical for regulatory compliance and legal defensibility of AI-assisted customs decisions.

---

## 5. PATH 2 — Zero-Shot Manifest Inspector (OWL-ViT v2 + SAM 2)

### What It Does
Verifies whether the contents physically visible in the X-ray scan **match the declared items** on the cargo manifest (invoice/packing list). Detects undeclared items and flags missing declared goods.


### Model Details

| Property | Value |
|---|---|
| Detection Model | OWL-ViT v2 (`google/owlv2-base-patch16-ensemble`) |
| Segmentation Model | SAM 2 (`sam2_b.pt`) |
| Approach | Open-vocabulary (zero-shot) — no retraining needed for new item types |
| Device Priority | CUDA → MPS (Apple Silicon) → CPU |

### Why Two Models?
- **OWL-ViT v2** is a vision-language model. You give it text like `"laptop"` and an image, and it finds where laptops are in the image. It works without ever being trained on your specific dataset.
- **SAM 2** (Segment Anything Model) takes the bounding boxes from OWL-ViT and generates pixel-precise masks (outlines) around each detected object.

### Pipeline Steps (7 Stages)

```
X-ray Image + Manifest Labels
    │
    ▼
┌──────────────────────────────┐
│  Stage 1: Domain Sweep       │
│  "Find everything"           │
│  • Run OWL-ViT with 21       │
│    generic queries like       │
│    "a physical object",       │
│    "a device", "a weapon"     │
│  • Returns ALL visible items  │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Stage 2: Manifest Sweep     │
│  "Find specific items"       │
│  • Per-label iterative mode   │
│  • For each manifest label,   │
│    run OWL-ViT with 3         │
│    prompt variants:            │
│    - "laptop"                  │
│    - "an x-ray of laptop"     │
│    - "a scan showing laptop"  │
│  • Lower threshold (0.125)    │
│    for maximum recall          │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Stage 3: NMS Deduplication  │
│  • Remove overlapping boxes   │
│    within each pass            │
│  • IoU threshold: 0.30        │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Stage 4: IoU Reconciliation │
│  • Cross-reference generic    │
│    detections vs manifest     │
│    detections                  │
│  • If a generic box overlaps  │
│    a manifest box → DECLARED  │
│  • If no overlap → UNDECLARED │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Stage 5: Missing Item Check │
│  • Any manifest label with    │
│    ZERO visual matches is     │
│    flagged as MISSING          │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Stage 6: SAM 2 Segmentation│
│  • Pixel-precise masks for    │
│    every detected item         │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Stage 7: Cargo Verdict      │
│  • CLEAR                      │
│  • UNDECLARED ITEMS DETECTED  │
│  • MISSING DECLARED GOODS     │
│  • CRITICAL: MIXED            │
└──────────────────────────────┘
```


### Verdict Logic

| Condition | Verdict |
|---|---|
| No undeclared items, no missing items | `CLEAR` |
| Undeclared items found, no missing items | `UNDECLARED ITEMS DETECTED` |
| No undeclared items, but declared items missing | `SUSPICIOUS: MISSING DECLARED GOODS` |
| Both undeclared AND missing items | `CRITICAL: UNDECLARED ITEMS + MISSING DECLARED GOODS` |


### Output
```json
{
  "zeroShot": {
    "overlayImage": "outputs/zero_shot_1775304499_ea6f7dbc.png",
    "verdict": "UNDECLARED ITEMS DETECTED",
    "totalObjects": 8,
    "declaredCount": 5,
    "undeclaredCount": 3,
    "missingCount": 0,
    "missingItems": [],
    "items": [
      {"index": 0, "status": "declared", "label": "laptop", "confidence": 0.87, "bbox": [...]},
      {"index": 1, "status": "undeclared", "label": "a weapon or knife", "confidence": 0.72, "bbox": [...]}
    ],
    "timings": {
      "sweep_detection": 2.105,
      "manifest_detection": 3.221,
      "nms": 0.002,
      "reconciliation": 0.001,
      "segmentation": 1.445,
      "total": 6.774
    }
  }
}
```

---

## 6. PATH 3 — SSIM Scan Comparison Service

### What It Does
Compares the current X-ray scan against a **reference scan** (e.g., a previous scan of the same container) to detect physical tampering or hidden modifications.

### When It Runs
This path **only runs when the user uploads a reference scan** alongside the primary X-ray image. If no reference is provided, this path is skipped entirely.

### Pipeline Steps (7 Stages)

```
Current Scan + Reference Scan
    │
    ▼
┌──────────────────────────────┐
│  Stage 1: Preprocess         │
│  • Convert to grayscale      │
│  • Resize to 800×640         │
│  • Histogram equalization    │
│  • Gaussian blur (5×5)       │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Stage 2: Image Alignment    │
│  • ECC (Enhanced Correlation │
│    Coefficient) alignment    │
│  • Corrects minor shifts,    │
│    rotations between scans   │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Stage 3: SSIM Computation   │
│  • Structural Similarity     │
│    Index Measure             │
│  • Score: 0.0 (completely    │
│    different) to 1.0         │
│    (identical)               │
│  • Generates pixel-level     │
│    difference map            │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Stage 4: Threshold          │
│  • Binary threshold at 30    │
│  • Isolates significant      │
│    structural changes only   │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Stage 5: Contour Detection  │
│  • Morphological cleanup     │
│    (dilate + erode)          │
│  • Find contour bounding     │
│    boxes around changed      │
│    regions                   │
│  • Filter: area ≥ 500 px     │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Stage 6: Heatmap            │
│  • Apply JET colormap to     │
│    the SSIM difference map   │
│  • Draw red bounding boxes   │
│    on the current scan       │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Stage 7: Interpretation     │
│  • Score ≥ 0.85 → "similar"  │
│  • Score < 0.85 → "different"│
└──────────────────────────────┘
```

### Configuration

| Parameter | Value | Purpose |
|---|---|---|
| `TARGET_SIZE` | 800 × 640 | Standardized comparison dimensions |
| `BLUR_KERNEL` | 5 × 5 | Noise reduction |
| `DIFF_THRESHOLD` | 30 | Binarization cut-off for change detection |
| `MIN_CONTOUR_AREA` | 500 px | Ignore tiny noise contours |
| `SSIM_SIMILAR_THRESHOLD` | 0.85 | Above this → "similar" |

### Output
```json
{
  "ssimScore": 0.7234,
  "ssimInterpretation": "different",
  "changedRegions": 3,
  "highlightHeatmap": "outputs/highlight_heatmap_1775304250.png",
  "outputHeatmap": "outputs/output_heatmap_1775304250.png"
}
```

---

## 7. Risk Aggregation Engine

### What It Does
Takes the outputs from all three parallel paths and produces a single, unified risk assessment for the shipment.

### Risk Scoring Algorithm

```
All Detections from YOLO
         │
         ▼
┌──────────────────────────┐
│  Classify Each Detection │
│  • Check against         │
│    PROHIBITED terms      │
│    {gun, bullet, knife}  │
│  • Check against         │
│    SUSPICIOUS terms      │
│    {baton, plier, hammer, │
│     powerbank, scissors,  │
│     wrench, sprayer,      │
│     handcuffs, lighter}   │
└──────────┬───────────────┘
           │
     ┌─────┼──────┐
     │     │      │
     ▼     ▼      ▼

 PROHIBITED   SUSPICIOUS   CLEAR
 Score: 90-100  Score: 50-75  Score: 0-20
```

### Scoring Formula

| Condition | Level | Score Range | Formula |
|---|---|---|---|
| Prohibited item found | `PROHIBITED` | 90 – 100 | `90 + (100 - 90) × max_confidence` |
| Suspicious item found | `SUSPICIOUS` | 50 – 75 | `50 + (75 - 50) × max_confidence` |
| No flagged items | `CLEAR` | 0 – 20 | `(1 - avg_confidence) × 20` |

### Future Enhancement: Invoice Value Risk Factor

An additional risk signal can come from the **manifest/invoice analysis**. The algorithm would:

1. **Parse the invoice PDF** to extract declared values (e.g., "Total: $500").
2. **Look up commodity min/max market values** from a reference database.
3. **Compare declared value against the expected range:**
   - If declared value is **below minimum** → Under-invoicing risk (possible duty evasion)
   - If declared value is **above maximum** → Over-invoicing risk (possible money laundering)
   - If declared value is **within range** → Normal
4. **Produce a value risk factor** (0-100) that is combined weight with the three model outputs.

```
Final Risk Score = w1 × YOLO_risk + w2 × ZeroShot_risk + w3 × SSIM_risk + w4 × Invoice_risk
```

Where `w1 + w2 + w3 + w4 = 1.0` (configurable weights).

### Output
```json
{
  "risk": {
    "level": "PROHIBITED",
    "score": 95,
    "reason": "Gun detected in shipment (1 total instance). Highest confidence: 94.0%. Prohibited threat item(s) found — immediate physical inspection and seizure protocol required.",
    "flags": ["gun"]
  }
}
```

---

## 8. Parallel Execution Strategy

### How The Three Paths Run Together

Currently, the three paths execute **sequentially** in the code (YOLO → GradCAM → SSIM → ZeroShot), but the architecture is designed so that:

1. **YOLO detection** runs first because the Risk Scorer depends on its output.
2. **GradCAM** uses the same YOLO model, so it runs immediately after.
3. **SSIM** is completely independent — it only needs the two images.
4. **Zero-Shot** is completely independent — it only needs the image + manifest labels.

### Result Aggregation Strategy

Each path returns its results independently. No path waits for another path's output:

| Path | Depends On | Can Fail Gracefully? |
|---|---|---|
| YOLO + GradCAM | Nothing (core path) | GradCAM can fail; YOLO must succeed |
| Zero-Shot | Manifest labels (optional) | Yes — wrapped in try/except |
| SSIM | Reference image (optional) | Yes — only runs if reference provided |

If YOLO detects a gun, the response is sent to the frontend immediately with `risk.level = "PROHIBITED"`. The Zero-Shot and SSIM results are included *alongside* this, providing additional context but not blocking the critical threat detection.

---


## 9. Audit Trail & Decentralized Storage

Every single pipeline execution generates a complete audit trail:

```
Pipeline Execution
    │
    ▼
┌──────────────────────┐
│  AuditTrail Object   │
│  • request_id (UUID) │
│  • timestamp         │
│  • steps[] array     │
│    (service, latency,│
│     input, output)   │
│  • final_status      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Fernet Encryption   │
│  (AES-128 CBC)       │
│  • Encrypt JSON with │
│    ENCRYPTION_KEY     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  IPFS Upload         │
│  (via Pinata API)    │
│  • Returns CID hash  │
│  • Tamper-proof      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Supabase Storage    │
│  • Maps request_id   │
│    to CID            │
│  • Stores created_at │
│    timestamp         │
└──────────────────────┘
```

### Audit Fields Logged Per Step

| Field | Example |
|---|---|
| `service` | `yolov8_detection`, `zero_shot_inspection`, `ssim_comparison` |
| `status` | `success` or `failed` |
| `input_data` | `{"filename": "scan.png", "image_size": [800, 640]}` |
| `output_data` | `{"detection_count": 3, "labels": ["gun", "knife"]}` |
| `latency` | `8.89` (seconds) |
| `model_version` | `model/best.pt` |

---



## 10. Complete File Reference

### Backend (`Model_Backend/`)

| File | Purpose | Key Functions |
|---|---|---|
| `main.py` | FastAPI application, all endpoints, pipeline orchestration | `analyze()`, `get_all_audits()`, `get_audit_by_request_id()` |
| `utils/detector.py` | YOLOv8 wrapper | `XRayDetector.detect()`, `XRayDetector.draw_boxes()` |
| `utils/gradcam.py` | GradCAM heatmap generation | `generate_gradcam()`, `overlay_heatmap()` |
| `utils/zero_shot_inspector.py` | OWL-ViT v2 + SAM 2 manifest verification | `ZeroShotManifestInspector.inspect()` |
| `utils/image_comparator.py` | SSIM scan comparison | `compare_scans()` |
| `utils/risk_scorer.py` | Threat classification | `calculate_risk()` |
| `utils/audit.py` | Generic audit logger | `AuditTrail` class |
| `utils/encryption.py` | Fernet encrypt/decrypt | `encrypt_data()`, `decrypt_data()` |
| `utils/ipfs_client.py` | Pinata IPFS upload/fetch | `upload_to_ipfs()`, `fetch_from_ipfs()` |
| `utils/supabase_client.py` | Supabase REST client | `store_audit_metadata()`, `query_audits()` |


### Frontend (`frontend/src/`)

| File | Purpose |
|---|---|
| `App.jsx` | Main application layout & state management |
| `components/ImageUploader.jsx` | X-ray image upload UI |
| `components/AnnotatedImage.jsx` | Bounding box overlay on X-ray |
| `components/GradCamHeatmap.jsx` | GradCAM heatmap display |
| `components/ScanHeatmapComparison.jsx` | SSIM comparison view |
| `components/ZeroShotOutput.jsx` | Zero-shot inspection results |
| `components/RiskBadge.jsx` | Risk level indicator |
| `components/DetectionList.jsx` | List of detected items |
| `components/ManifestComparison.jsx` | Manifest vs detection comparison |
| `components/DownloadReport.jsx` | PDF report generation |
| `hooks/useDetections.js` | API communication hook |

---



## 11. API Endpoints Summary

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/analyze` | Run full AI pipeline on X-ray image |
| `GET` | `/api/audit/logs` | Fetch audit history (date-wise filtering) |
| `GET` | `/api/audit/logs/{request_id}` | Fetch & decrypt full audit report |
| `POST` | `/api/manifest/extract` | Parse manifest PDF and extract item names |
| `GET` | `/api/files?path=...` | Serve generated output images |
| `GET` | `/api/health` | Health check |

---

## 12. Dependencies

### Backend (Python)
```
ultralytics          # YOLOv8 + SAM 2
transformers         # OWL-ViT v2 (Hugging Face)
torch, torchvision   # PyTorch
opencv-python        # Image processing
scikit-image         # SSIM computation
Pillow               # Image I/O
fastapi, uvicorn     # Web framework
pdfplumber           # PDF parsing
requests             # HTTP client (Pinata, Supabase)
python-dotenv        # Environment variable management
cryptography         # Fernet encryption
```

### Frontend (React)
```
react                # UI framework
framer-motion        # Animations
lucide-react         # Icons
```

---

**Status: System Architecture Documentation — Complete ✅**
