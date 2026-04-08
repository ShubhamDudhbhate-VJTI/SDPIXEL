# CargoGuard — Audit System README
**Detailed Technical Documentation for the Decentralized AI Pipeline Audit Trail**

---

## What Is This?

Every time a customs officer uploads an X-ray image and clicks "Analyze", our platform runs multiple AI models (YOLO, GradCAM, Zero-Shot, SSIM). But how do you prove what the AI actually did? What if someone questions the results in court? What if there's a dispute about whether the AI flagged a gun or missed it?

**That's where the Audit System comes in.**

It silently records every single thing every model does — what it received, what it predicted, how long it took, and whether it succeeded or failed. Then it encrypts that record, uploads it to a permanent decentralized network (IPFS), and saves a lookup key in a database (Supabase). Nobody can tamper with it. Nobody can delete it. It's a permanent, encrypted, verifiable receipt of every AI decision.

---

## How Logs Are Collected From All Models

### The AuditTrail Class (`utils/audit.py`)

At the very beginning of every analysis request, before any model runs, we create a fresh `AuditTrail` object:

```python
audit = AuditTrail()
```

This object is like a blank notebook. It automatically generates:
- A unique `request_id` (UUID) — e.g., `4f82a5c6-a6ed-429f-af46-1e5b4a3debe3`
- A precise `timestamp` — e.g., `2026-04-04T12:00:23.593817`
- An empty `steps[]` array — waiting to be filled

### How Each Model Writes to the Notebook

As the pipeline progresses, every single model/service writes exactly one entry (called a "step") into this notebook. Here's the exact sequence:

#### Step 1: Manifest PDF Extraction
```python
audit.log_step(
    service="manifest_extraction",
    status="success",
    input_data={"filename": "invoice.pdf"},
    output_data={"item_count": 4, "items": ["laptop", "phone", "cables", "shoes"]},
    latency=0.342,   # seconds
)
```
**What this captures:** The manifest parser read 4 items from the uploaded PDF in 0.342 seconds.

#### Step 2: YOLOv8 Object Detection
```python
audit.log_step(
    service="yolov8_detection",
    status="success",
    input_data={"filename": "scan.png", "image_size": [1920, 1080]},
    output_data={"detection_count": 3, "labels": ["gun", "knife", "scissors"]},
    latency=8.89,
    model_version="model/best.pt",
)
```
**What this captures:** YOLO detected 3 objects (gun, knife, scissors) in 8.89 seconds using model version `best.pt`.

#### Step 3: Risk Scoring
```python
audit.log_step(
    service="risk_scoring",
    status="success",
    input_data={"detection_count": 3},
    output_data={"level": "PROHIBITED", "score": 95},
    latency=0.001,
)
```
**What this captures:** The risk engine classified the shipment as PROHIBITED with score 95 in 1 millisecond.

#### Step 4: GradCAM Heatmap Generation
```python
audit.log_step(
    service="gradcam_generation",
    status="success",
    input_data={"image_size": [1920, 1080]},
    output_data={"output_path": "outputs/gradcam_1775304250.png"},
    latency=2.15,
)
```
**What this captures:** GradCAM generated the explainability heatmap in 2.15 seconds.

#### Step 5: SSIM Scan Comparison (if reference scan provided)
```python
audit.log_step(
    service="ssim_comparison",
    status="success",
    input_data={"has_reference": True},
    output_data={"ssim_score": 0.7234, "interpretation": "different", "changed_regions": 3},
    latency=1.02,
)
```
**What this captures:** The SSIM service found 3 changed regions between the current and reference scans, with a similarity score of 0.7234.

#### Step 6: Zero-Shot Manifest Inspection
```python
audit.log_step(
    service="zero_shot_inspection",
    status="success",
    input_data={"label_count": 4, "labels": ["laptop", "phone", "cables", "shoes"]},
    output_data={
        "verdict": "UNDECLARED ITEMS DETECTED",
        "total_objects": 8,
        "declared_count": 5,
        "undeclared_count": 3,
        "missing_count": 0,
    },
    latency=6.77,
)
```
**What this captures:** Zero-Shot found 8 physical objects, matched 5 to the manifest, flagged 3 as undeclared, in 6.77 seconds.

### What If a Model Fails?

If any model crashes (e.g., GradCAM throws an exception), the audit still records it:

```python
audit.log_step(
    service="gradcam_generation",
    status="failed",
    error="RuntimeError: CUDA out of memory",
)
```

The pipeline continues running other models. The audit captures both successes AND failures.

---

## The Complete Audit JSON

After all models finish, the audit is finalized:

```python
audit_json = audit.finalize("success")
```

This produces a complete JSON document like this:

```json
{
  "request_id": "4f82a5c6-a6ed-429f-af46-1e5b4a3debe3",
  "timestamp": "2026-04-04T12:00:23.593817",
  "final_status": "success",
  "steps": [
    {
      "service": "manifest_extraction",
      "status": "success",
      "start_time": 1775304023.22,
      "end_time": 1775304023.56,
      "latency_ms": 342.0,
      "input_data": {"filename": "invoice.pdf"},
      "output_data": {"item_count": 4, "items": ["laptop", "phone", "cables", "shoes"]}
    },
    {
      "service": "yolov8_detection",
      "status": "success",
      "start_time": 1775304023.56,
      "end_time": 1775304032.45,
      "latency_ms": 8890.0,
      "input_data": {"filename": "scan.png", "image_size": [1920, 1080]},
      "output_data": {"detection_count": 3, "labels": ["gun", "knife", "scissors"]},
      "model_version": "model/best.pt"
    },
    {
      "service": "risk_scoring",
      "status": "success",
      "latency_ms": 1.0,
      "output_data": {"level": "PROHIBITED", "score": 95}
    },
    {
      "service": "gradcam_generation",
      "status": "success",
      "latency_ms": 2150.0,
      "output_data": {"output_path": "outputs/gradcam_1775304250.png"}
    },
    {
      "service": "ssim_comparison",
      "status": "success",
      "latency_ms": 1020.0,
      "output_data": {"ssim_score": 0.7234, "changed_regions": 3}
    },
    {
      "service": "zero_shot_inspection",
      "status": "success",
      "latency_ms": 6770.0,
      "output_data": {"verdict": "UNDECLARED ITEMS DETECTED", "undeclared_count": 3}
    }
  ]
}
```

This JSON is the **complete forensic record** of what happened during that scan. Every service, every input, every output, every millisecond.

---

## How We Upload to Pinata (IPFS)

### Why IPFS/Pinata?

Regular databases (SQL, MongoDB) can be edited or deleted by an admin. IPFS is fundamentally different:
- Files are addressed by their **content hash (CID)**. If you change even one character, the CID changes completely.
- Files are distributed across **thousands of nodes** globally. No single entity can delete them.
- Pinata is a **managed IPFS gateway** that makes uploading/fetching easy via REST API.

### The Upload Flow (Step by Step)

```
                    Audit JSON (ready)
                         │
                         ▼
              ┌─────────────────────┐
              │  Step 1: ENCRYPT    │
              │                     │
              │  encrypt_data(      │
              │    audit_json       │
              │  )                  │
              │                     │
              │  Takes the readable │
              │  JSON and scrambles │
              │  it using Fernet    │
              │  AES-128 encryption │
              │  with the key from  │
              │  .env file          │
              │                     │
              │  Input:             │
              │  {"request_id":...} │
              │                     │
              │  Output:            │
              │  "gAAAAABl2Kx..."   │
              │  (unreadable)       │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  Step 2: PACKAGE    │
              │                     │
              │  Wrap the encrypted │
              │  string inside a    │
              │  JSON envelope:     │
              │                     │
              │  {                  │
              │   "encrypted_       │
              │    payload":        │
              │   "gAAAAABl2Kx..."  │
              │  }                  │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  Step 3: UPLOAD     │
              │                     │
              │  HTTP POST to       │
              │  Pinata API:        │
              │                     │
              │  POST https://      │
              │  api.pinata.cloud/  │
              │  pinning/           │
              │  pinJSONToIPFS      │
              │                     │
              │  Headers:           │
              │  Authorization:     │
              │  Bearer <JWT>       │
              │                     │
              │  Body:              │
              │  {                  │
              │   pinataContent:    │
              │   {encrypted...},   │
              │   pinataMetadata:   │
              │   {name: req_id}    │
              │  }                  │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  Step 4: GET CID    │
              │                     │
              │  Pinata responds:   │
              │  {                  │
              │   "IpfsHash":       │
              │   "QmTas4HQa8ZPj.." │
              │  }                  │
              │                     │
              │  This CID is the    │
              │  permanent address  │
              │  of this audit on   │
              │  the IPFS network   │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  Step 5: STORE      │
              │  METADATA           │
              │                     │
              │  HTTP POST to       │
              │  Supabase:          │
              │                     │
              │  INSERT INTO        │
              │  audit_logs:        │
              │  {                  │
              │   cid: "QmTas4H..", │
              │   request_id:       │
              │    "4f82a5c6...",   │
              │   status: "success",│
              │   created_at: now() │
              │  }                  │
              └─────────────────────┘
```

### Why Encrypt Before Uploading?

IPFS is a **public network**. Anyone who knows the CID can download your file. By encrypting the audit JSON *before* uploading, we ensure:
- Even if someone discovers the CID, all they see is `gAAAAABl2Kx...` — unreadable gibberish.
- Only your backend server (which has the `ENCRYPTION_KEY` in `.env`) can decrypt it.
- The data is protected at rest AND in transit.


### Background Processing

The entire upload process (encrypt → Pinata → Supabase) runs as a **FastAPI BackgroundTask**:

```python
background_tasks.add_task(_upload_audit_to_ipfs, audit_json, audit.request_id)
```

This means:
- The frontend gets its response (detections, risk, images) **immediately**.
- The heavy IPFS upload happens silently in the background.
- The user never waits for the audit to finish uploading.

---

## How Fetching Works

### Fetching the History List

**Endpoint:** `GET /api/audit/logs`

```
Frontend                          Backend                         Supabase
   │                                │                                │
   │  GET /api/audit/logs           │                                │
   │  ?date_filter=04-04-2026       │                                │
   │ ──────────────────────────────►│                                │
   │                                │  Convert DD-MM-YYYY            │
   │                                │  to YYYY-MM-DD                 │
   │                                │                                │
   │                                │  SELECT * FROM audit_logs      │
   │                                │  WHERE created_at              │
   │                                │  BETWEEN '2026-04-04 00:00'    │
   │                                │  AND '2026-04-04 23:59'        │
   │                                │  ORDER BY created_at DESC      │
   │                                │ ──────────────────────────────►│
   │                                │                                │
   │                                │  ◄─── JSON Array of rows ─────│
   │                                │                                │
   │  ◄── {"logs": [{request_id,   │                                │
   │       created_at, status,      │                                │
   │       cid, description}]}      │                                │
   │                                │                                │
```

**What happens:** The backend queries Supabase for all audit records matching the given date. It returns a lightweight summary — no heavy files, no decryption. This is fast and instant.

### Fetching the Full Detailed Report

**Endpoint:** `GET /api/audit/logs/{request_id}`

```
Frontend                    Backend                    Supabase              Pinata/IPFS
   │                          │                          │                      │
   │  GET /api/audit/logs/    │                          │                      │
   │  4f82a5c6-a6ed-...       │                          │                      │
   │ ────────────────────────►│                          │                      │
   │                          │                          │                      │
   │                          │  SELECT cid              │                      │
   │                          │  FROM audit_logs         │                      │
   │                          │  WHERE request_id =      │                      │
   │                          │  '4f82a5c6...'           │                      │
   │                          │ ────────────────────────►│                      │
   │                          │                          │                      │
   │                          │  ◄── cid: "QmTas4H..."  │                      │
   │                          │                          │                      │
   │                          │  GET https://gateway.    │                      │
   │                          │  pinata.cloud/ipfs/      │                      │
   │                          │  QmTas4H...              │                      │
   │                          │ ──────────────────────────────────────────────►│
   │                          │                          │                      │
   │                          │  ◄── {"encrypted_payload": "gAAAAABl2Kx..."}  │
   │                          │                          │                      │
   │                          │  DECRYPT using           │                      │
   │                          │  ENCRYPTION_KEY          │                      │
   │                          │  from .env               │                      │
   │                          │                          │                      │
   │  ◄── {"audit": {         │                          │                      │
   │       request_id,         │                          │                      │
   │       timestamp,          │                          │                      │
   │       steps: [...]        │                          │                      │
   │      },                   │                          │                      │
   │      "metadata": {        │                          │                      │
   │       created_at, cid     │                          │                      │
   │      }}                   │                          │                      │
```

**What happens (5 steps):**
1. Frontend sends the `request_id` (which it got from the history list)
2. Backend asks Supabase: *"What is the CID for this request_id?"*
3. Backend asks Pinata/IPFS: *"Download the file at this CID"*
4. Backend receives the encrypted blob and decrypts it using `ENCRYPTION_KEY`
5. Backend returns the full, readable audit JSON to the frontend

### Backwards Compatibility

If the CID points to an **older scan** (from before encryption was enabled), the backend checks:
```python
encrypted_string = secure_payload.get("encrypted_payload")
if not encrypted_string:
    # Old unencrypted scan — return as-is
    return {"audit": secure_payload}
```

This ensures no old data is ever broken.

---

## File Structure

```
Model_Backend/
├── utils/
│   ├── audit.py              ← AuditTrail class (the notebook)
│   ├── encryption.py         ← Fernet encrypt/decrypt functions
│   ├── ipfs_client.py        ← upload_to_ipfs() + fetch_from_ipfs()
│   └── supabase_client.py    ← store_audit_metadata() + query_audits()
├── main.py                   ← Pipeline integration + API endpoints
└── .env                      ← Secret keys (NEVER committed to Git)
```

---

## Environment Variables

```env
# Pinata (IPFS Gateway)
PINATA_JWT=eyJhbGciOi...your_pinata_jwt_token

# Supabase (Database)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOi...your_supabase_anon_key

# Encryption
ENCRYPTION_KEY=hbLk1t_T7awAS4BCDbfmHUMrJQwzOO9u4oxj24TI0BU=
```

**Generate a new encryption key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Supabase Table Schema

Table: `audit_logs`

| Column | Type | Auto? | Description |
|---|---|---|---|
| `id` | int8 | ✅ Auto-increment | Primary key |
| `cid` | text | ❌ | IPFS Content Identifier from Pinata |
| `request_id` | text | ❌ | UUID generated per analysis |
| `user_id` | text | ❌ | User identifier (default: `default_user`) |
| `status` | text | ❌ | `success` or `failed` |
| `description` | text | ❌ | Summary of pipeline steps |
| `created_at` | timestamptz | ❌ | UTC timestamp of creation |

---

## Security Model

```
┌─────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Layer 1: Encryption at Rest                        │
│  • Fernet AES-128 CBC encryption                    │
│  • Key stored ONLY in server .env file              │
│  • Data encrypted BEFORE leaving the server         │
│                                                     │
│  Layer 2: Content-Addressed Storage (IPFS)          │
│  • CID = SHA-256 hash of file contents              │
│  • Any modification = different CID                 │
│  • Proves file hasn't been tampered with            │
│                                                     │
│  Layer 3: Database Access Control (Supabase)        │
│  • Row-Level Security (RLS) available               │
│  • API key required for all queries                 │
│  • HTTPS encrypted in transit                       │
│                                                     │
│  Layer 4: .env Protection                           │
│  • .gitignore blocks .env from GitHub               │
│  • Keys never exposed in source code                │
│                                                     │
└─────────────────────────────────────────────────────┘
```
```python
audit.log_step(
    service="manifest_extraction",
    status="success",
    input_data={"filename": "invoice.pdf"},
    output_data={"item_count": 4, "items": ["laptop", "phone", "cables", "shoes"]},
    latency=0.342,   # seconds
)
```
---

## Complete Data Flow Summary


```
User clicks "Analyze"
        │
        ▼
┌──────────────────┐     ┌──────────────────┐
│  AuditTrail()    │     │  AI Models Run:   │
│  created with    │◄────│  • YOLO           │
│  empty steps[]   │     │  • GradCAM        │
│                  │     │  • SSIM           │
│  Each model      │     │  • Zero-Shot      │
│  writes one      │     │  Each writes      │
│  step entry      │     │  to audit.steps[] │
└────────┬─────────┘     └──────────────────┘
         │
         ▼
┌──────────────────┐
│  audit.finalize  │
│  ("success")     │
│  → Complete JSON │
└────────┬─────────┘
         │
         ├──► Frontend gets response (detections, risk, images)
         │    immediately — no waiting
         │
         ▼  (Background Task — non-blocking)
┌──────────────────┐
│  encrypt_data()  │
│  Fernet AES-128  │
│  "gAAAAABl2Kx.." │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  upload_to_ipfs()│
│  POST → Pinata   │
│  Returns CID     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  store_metadata()│
│  POST → Supabase │
│  Maps request_id │
│  → CID           │
└──────────────────┘
         │
         ▼
    ✅ Permanent, encrypted,
       tamper-proof audit stored
```

---

## Dependencies

```bash
pip install requests python-dotenv cryptography

```

---

**Status: Audit System — 100% Production Ready ✅**

