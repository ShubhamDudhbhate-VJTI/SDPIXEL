# CargoGuard AI Audit System — Complete Integration Guide
**Version 2.0 (Final)**

This document serves as the official API integration guide for the Decentralized AI Audit System. All core backend functionality is complete: pipeline logging, IPFS pinning, Supabase DB tracking, Fernet encryption, date-wise fetching, and decryption endpoints.

Use this documentation to integrate your React Frontend correctly.

---

## Architecture Overview

```
User uploads X-ray
       │
       ▼
POST /api/analyze  ──►  YOLO + GradCAM + ZeroShot + Risk Scoring
       │
       ├──► Returns detections + request_id to Frontend
       │
       └──► Background Task (silent, non-blocking):
              │
              ├── 1. AuditTrail collects all step logs
              ├── 2. Fernet encrypts the JSON payload
              ├── 3. Uploads encrypted blob to IPFS via Pinata → gets CID
              └── 4. Stores CID + metadata in Supabase
```

**1. Create & Encrypt (Silent):** Whenever `POST /api/analyze` is called, an internal `AuditTrail` is automatically generated, tracking time, model predictions, and statuses. Before upload, the payload is securely scrambled using `Fernet` AES-128 Symmetric Encryption.

**2. Permanent Storage:** That scrambled JSON is then uploaded to IPFS via the **Pinata API**, securing its permanent spot on a decentralized network. Each file gets a unique CID (Content Identifier) — a cryptographic hash tied to the file's contents.

**3. Database Lookup:** The CID is mapped to a UUID (`request_id`) and saved into the **Supabase** `audit_logs` table alongside its `created_at` timestamp, status, and description.

---

## Backend Files Reference

| File | Purpose |
|---|---|
| `utils/audit.py` | Generic `AuditTrail` class — logs pipeline steps, latencies, metadata |
| `utils/encryption.py` | Fernet encrypt/decrypt functions using `ENCRYPTION_KEY` from `.env` |
| `utils/ipfs_client.py` | `upload_to_ipfs()` and `fetch_from_ipfs()` via Pinata API |
| `utils/supabase_client.py` | `store_audit_metadata()` and `query_audits()` via Supabase REST API |
| `main.py` | FastAPI endpoints — integrates all of the above |

---

## Environment Variables (`.env`)

All four must be present in `Model_Backend/.env`:

```env
PINATA_JWT=your_pinata_jwt_token
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
ENCRYPTION_KEY=your_fernet_key_here
```

> **⚠️ CRITICAL:** If `ENCRYPTION_KEY` is missing, the server generates a temporary key. After a restart, all previously encrypted data becomes **permanently unreadable**. Always set this value.

To generate a new key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Supabase Table Schema

Table name: `audit_logs`

| Column | Type | Description |
|---|---|---|
| `id` | int8 (auto) | Primary key |
| `cid` | text | IPFS Content Identifier from Pinata |
| `request_id` | text | UUID generated per analysis request |
| `user_id` | text | Optional user identifier |
| `status` | text | `success` or `failed` |
| `description` | text | Summary of pipeline steps executed |
| `created_at` | timestamptz (auto) | When the audit was created |

---

## Integration Endpoints

All endpoints are active under `http://localhost:8000`.

---

### 1. `POST /api/analyze` — The Main Trigger
Runs the AI pipeline. Silently triggers audit upload in the background.

*   **Request:** `multipart/form-data` with X-ray image file
*   **Response:**
    ```json
    {
      "detections": [...],
      "risk": { "level": "high", "score": 85, "reason": "..." },
      "outputs": { "gradcam": "...", "zeroShot": {...} },
      "request_id": "834f8c6b-31d7-4df3-aa6a-cf6c98fc0a21"
    }
    ```
*   **Frontend Action:** Save the `request_id` from the response. This ID links to the full audit trail.

---

### 2. `GET /api/audit/logs` — Fetch History List (Date-wise)
Returns a lightweight summary list of past scan audits from Supabase.

*   **Query Parameters (all optional):**

| Parameter | Type | Format | Description |
|---|---|---|---|
| `date_filter` | string | `DD-MM-YYYY` | Filter logs by a specific date (e.g. `04-04-2026`) |
| `limit` | int | number | Max records to return. Leave blank for all records |

*   **Example Requests:**
    ```
    GET /api/audit/logs                          → All logs (no limit)
    GET /api/audit/logs?date_filter=04-04-2026   → All logs from April 4th
    GET /api/audit/logs?date_filter=04-04-2026&limit=10  → First 10 logs from April 4th
    ```

*   **Response:**
    ```json
    {
      "logs": [
        {
          "id": 142,
          "created_at": "2026-04-04T12:00:23Z",
          "request_id": "834f8c6b-31d7-4df3-aa6a-cf6c98fc0a21",
          "status": "success",
          "description": "Pipeline: XRayDetector, RiskScorer, GradCAM, SSIM, ZeroShot. Status: success",
          "cid": "Qmdj6Mn62cD7fyMhudhFCHuJnHQX6jwe7..."
        }
      ]
    }
    ```

*   **Error Responses:**
    * `400` — Invalid date format (not `DD-MM-YYYY`)
    * `500` — Supabase connection failed

*   **Frontend Action:** Use this to populate a "History Table". Each row displays the date, status, and description. Attach an `onClick` handler to each row.

---

### 3. `GET /api/audit/logs/{request_id}` — Fetch Full Detailed Report
Downloads the encrypted audit from IPFS, decrypts it, and returns the complete pipeline execution log.

*   **Path Parameter:**

| Parameter | Type | Description |
|---|---|---|
| `request_id` | string | The UUID from the scan (e.g. `834f8c6b-31d7-4df3-aa6a-cf6c98fc0a21`) |

*   **Internal Flow:**
    1. Queries Supabase to find the CID for this `request_id`
    2. Fetches the encrypted blob from IPFS/Pinata using the CID
    3. Decrypts the payload using `ENCRYPTION_KEY` from `.env`
    4. Returns the readable JSON

*   **Response:**
    ```json
    {
      "audit": {
        "request_id": "834f8c6b-31d7-4df3-aa6a-cf6c98fc0a21",
        "timestamp": "2026-04-04T12:00:23.593817",
        "final_status": "success",
        "steps": [
          {
            "service": "XRayDetector",
            "start_time": 177530432.22,
            "end_time": 177530441.11,
            "latency_ms": 8890.0,
            "status": "success",
            "output_snippet": [{"class": "gun", "confidence": 0.94}]
          },
          {
            "service": "RiskScorer",
            "start_time": 177530441.11,
            "end_time": 177530441.15,
            "latency_ms": 40.0,
            "status": "success",
            "output_snippet": {"level": "high", "score": 85}
          }
        ]
      },
      "metadata": {
        "id": 142,
        "created_at": "2026-04-04T12:00:23Z",
        "status": "success",
        "cid": "Qmdj6Mn62cD7fyMhudhFCHuJnHQX6jwe7..."
      }
    }
    ```

*   **Error Responses:**
    * `404` — No audit found for this `request_id`
    * `500` — IPFS fetch or decryption failed

*   **Frontend Action:** When user clicks a row from Endpoint 2, call this endpoint with the row's `request_id`. Display the returned `steps` array as a detailed breakdown.

---

## Frontend Integration Example (React)

```javascript
const API_BASE = "http://localhost:8000";

// 1. Fetch today's audit history
async function fetchAuditHistory(date) {
  const res = await fetch(`${API_BASE}/api/audit/logs?date_filter=${date}`);
  const data = await res.json();
  return data.logs; // Array of summary objects
}

// 2. Fetch full details for a specific scan
async function fetchAuditDetail(requestId) {
  const res = await fetch(`${API_BASE}/api/audit/logs/${requestId}`);
  const data = await res.json();
  return data.audit; // Full decrypted audit JSON
}

// 3. Usage in a React component
function AuditHistoryTable() {
  const [logs, setLogs] = useState([]);
  const [selectedAudit, setSelectedAudit] = useState(null);

  useEffect(() => {
    const today = new Date().toLocaleDateString('en-GB').replace(/\//g, '-');
    fetchAuditHistory(today).then(setLogs);
  }, []);

  const handleRowClick = async (requestId) => {
    const detail = await fetchAuditDetail(requestId);
    setSelectedAudit(detail);
  };

  return (
    <table>
      <thead>
        <tr><th>Date</th><th>Status</th><th>Actions</th></tr>
      </thead>
      <tbody>
        {logs.map(log => (
          <tr key={log.request_id}>
            <td>{new Date(log.created_at).toLocaleString()}</td>
            <td>{log.status}</td>
            <td><button onClick={() => handleRowClick(log.request_id)}>View Details</button></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

---

## Edge Cases Handled

| Edge Case | Handling |
|---|---|
| Old unencrypted scans on IPFS | Backwards compatible — returns raw JSON if no `encrypted_payload` field |
| Invalid date format | Returns `400 Bad Request` with clear error message |
| `request_id` not found in Supabase | Returns `404 Not Found` |
| Pinata/Supabase down during scan | Background task fails silently; main scan still returns results to user |
| Missing `ENCRYPTION_KEY` | Logs a warning; generates temp key (data lost on restart) |

---

## Testing via Swagger UI

1. Start backend: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
2. Open browser: `http://localhost:8000/docs`
3. Test `GET /api/audit/logs` with `date_filter=04-04-2026`
4. Copy a `request_id` from the response
5. Test `GET /api/audit/logs/{request_id}` with that ID
6. Confirm decrypted audit JSON is returned successfully

---

## Dependencies

```
pip install requests python-dotenv cryptography
```

---

**Status: Audit System Backend — 100% Complete ✅**
