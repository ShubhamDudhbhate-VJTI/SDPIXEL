# PIXEL - AI-Powered X-Ray Inspection Platform
## Deployment Presentation Slides

---

# Slide 1: System Architecture & Deployment Overview

## 1.1 Deployed Architecture Stack

| Layer | Technology | Platform | Purpose |
|-------|------------|----------|---------|
| **Frontend** | React 19 + Vite 8 | Vercel | User interface, static hosting |
| **Backend** | FastAPI + Uvicorn | Railway (Docker) | API server, ML inference |
| **ML Pipeline** | YOLO→GradCAM→SHAP (seq) + SSIM/Parsing/Zero-Shot (para) | Railway | Hybrid inference |detection, segmentation |
| **Database** | PostgreSQL | Supabase | Structured data storage |
| **Storage** | IPFS | Pinata Gateway | Tamper-proof audit logs |
| **Security** | Fernet Encryption | Backend | Audit log encryption |

## 1.2 Complete Data Flow Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────────────┐
│   USER BROWSER  │────▶│  VERCEL (React) │────▶│    RAILWAY (FastAPI)        │
└─────────────────┘     └─────────────────┘     └──────────────┬──────────────┘
                                                             │
                                                             │ Trigger Analysis
                                                             ▼
                    ┌─────────────────────────────────────────────────────────────────────────┐
                    │                    HYBRID PROCESSING PIPELINE                           │
                    │                                                                           │
                    │  ┌─────────────────────────────────┐    ┌─────────────────────────────┐  │
                    │  │   SEQUENTIAL CHAIN (Main)       │    │   PARALLEL SERVICES         │  │
                    │  │                                 │    │                             │  │
                    │  │  ┌─────────┐    ┌─────────┐     │    │  ┌─────────┐  ┌─────────┐ │  │
                    │  │  │  YOLO   │───▶│ GradCAM │────┐│    │  │  SSIM   │  │  Parse  │ │  │
                    │  │  │  V8     │    │ Heatmap │    ││    │  │ Service │  │ Manifest│ │  │
                    │  │  └─────────┘    └─────────┘    ││    │  └─────────┘  └─────────┘ │  │
                    │  │                                ▼│    │                             │  │
                    │  │                         ┌─────────┐│    │  ┌─────────────────────┐  │  │
                    │  │                         │  SHAP   ││    │  │   ZERO-SHOT         │  │  │
                    │  │                         │Explainer││    │  │   (OWL-ViT)         │  │  │
                    │  │                         └────┬────┘│    │  │   Fallback/Enhance  │  │  │
                    │  └──────────────────────────────┼─────┘    │  └─────────────────────┘  │  │
                    │                                     │        └─────────────────────────────┘  │
                    │                                     │                    │                  │
                    │                                     └────────────────────┘                  │
                    │                                                      │                        │
                    │                                                      ▼                        │
                    │                                         ┌─────────────────┐                 │
                    │                                         │  RESULT MERGER  │                 │
                    │                                         │  + Aggregator   │                 │
                    │                                         └────────┬────────┘                 │
                    └──────────────────────────────────────────────────┼───────────────────────────┘
                                                                       │
                              ┌────────────────────────────┼────────────────────────────┐
                              │                            │                            │
                              ▼                            ▼                            ▼
                    ┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
                    │  SUPABASE (DB)  │          │ RAILWAY VOLUME  │          │ PINATA (IPFS)   │
                    │  • Manifests    │          │  • YOLOv8       │          │  • Audit logs   │
                    │  • Detections   │          │  • GradCAM      │          │  • CIDs         │
                    │  • SHAP Values  │          │  • SSIM Ref     │          │  • Timestamps   │
                    │  • Shipments    │          │  • OWL-ViT      │          │                 │
                    └─────────────────┘          └─────────────────┘          └─────────────────┘
                                                                       │
                                                                       ▼
                                                        ┌─────────────────────────────┐
                                                        │        RESPONSE BACK        │
                                                        │  • YOLO Detections          │
                                                        │  • GradCAM Heatmaps         │
                                                        │  • SHAP Explanations        │
                                                        │  • SSIM Similarity Scores   │
                                                        │  • Manifest Parsed Data     │
                                                        │  • Zero-shot Detections     │
                                                        │  • Aggregated Confidence    │
                                                        └─────────────────────────────┘
```───────────┬────────────────────────────────┘
                                         │
                                         │ JSON Response
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. FRONTEND: Display results                                          │
                    - Render detection bounding boxes                                   │
                    - Show contraband classification                                    │
                    - Display confidence scores                                         │
                    - Enable report export                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

## 1.3 Component Responsibilities

### Frontend (Vercel)
- **Framework**: React 19 with React Router 7
- **Styling**: Tailwind CSS 3.4 + Framer Motion animations
- **Build Output**: Static files in `dist/` folder
- **Deployment**: Git-triggered automatic builds
- **Features**:
  - X-ray image upload (drag & drop)
  - Real-time detection visualization
  - Manifest PDF upload & extraction
  - Results dashboard with export

### Backend (Railway Docker)
- **Framework**: FastAPI with Uvicorn ASGI server
- **Runtime**: Python 3.11-slim container
- **Port**: Dynamic `$PORT` (Railway assigns)
- **Health Check**: `GET /api/health` (configured in railway.toml)
- **Key Endpoints**:
  - `POST /api/analyze` - Full X-ray analysis pipeline
  - `POST /api/manifest/extract` - PDF text extraction
  - `GET /api/files` - Serve generated outputs
  - `POST /api/audit/log` - Encrypted audit logging

### Hybrid ML Pipeline Services

#### Sequential Chain (Main Pipeline)
| Stage | Service | Model/Method | Size | Purpose |
|-------|---------|--------------|------|---------|
| **1** | YOLOv8 | `best.pt` | ~6MB | Object detection - bounding boxes |
| **2** | GradCAM | YOLO hooks | Runtime | Attention heatmap generation |
| **3** | SHAP | DeepExplainer | Runtime | Feature importance explanation |

#### Independent Parallel Services (Run Simultaneously)
| Service | Model/Method | Size | Purpose | Relation to Main Chain |
|---------|--------------|------|---------|------------------------|
| **SSIM Service** | Structural Similarity Index | Runtime | Image comparison & anomaly detection | **Independent Parallel** |
| **Manifest Parsing** | pdfplumber/pymupdf | Runtime | PDF text extraction & structuring | Async parallel |
| **Zero-Shot (OWL-ViT)** | `google/owlvit-base` | ~800MB | Open-vocabulary detection fallback | Async parallel |

### Database (Supabase)
- **Engine**: PostgreSQL 15
- **Tables**:
  - `shipments` - Shipment records with encrypted metadata
  - `xray_detections` - Detection results per scan
  - `audit_logs` - Encrypted compliance logs
- **Features**: Row Level Security (RLS), REST API, Realtime subscriptions

### Storage (Pinata IPFS)
- **Service**: Pinata Cloud IPFS pinning
- **Content**: Encrypted audit log files
- **Access**: JWT-authenticated gateway requests
- **Benefit**: Tamper-proof, timestamped, globally accessible

## 1.4 Architecture Highlights

| Feature | Implementation | Benefit |
|---------|----------------|---------|
| **Cloud-Native** | Vercel Edge + Railway Containers | Auto-scaling, global CDN |
| **Separation of Concerns** | Frontend static / Backend stateful | Independent scaling |
| **Security-First** | Encryption at rest + in transit | Compliance ready |
| **Cost-Optimized** | Free tiers on Vercel + Railway | $0 for development |
| **Production-Ready** | Health checks, auto-restart, logging | 99.9% uptime |

---

# Slide 2: Pre-Deployment Preparation & Security

## 2.1 Repository Cleanup Checklist

### Environment Files Management
| File | Action | Location |
|------|--------|----------|
| `.env` | **REMOVE from Git** | `Model_Backend/.env` |
| `.env` | **REMOVE from Git** | `Frontend/.env` |
| `.env.example` | **KEEP** (template) | `Model_Backend/.env.example` |
| `.env.example` | **KEEP** (template) | `Frontend/.env.example` |

**Command to remove tracked .env files:**
```bash
git rm --cached Model_Backend/.env Frontend/.env
git commit -m "Remove .env files from tracking"
```

### Large Model Files (>100MB) - Gitignore
```gitignore
# Large ML Models (managed via Railway Volume or external storage)
*.pt
*.pth
*.onnx
*.bin
*.safetensors
Model_Backend/model/

# Runtime outputs (generated at runtime)
Model_Backend/audit_logs/
Model_Backend/outputs/
Model_Backend/test_images/

# Build outputs
Frontend/dist/
Frontend/node_modules/
```

### Secrets & Security Files
```gitignore
# Secrets (CRITICAL - never commit)
.env
*.env
JWT_PINNATA.txt
*.key
*.pem
*.crt

# IDE files
.vscode/
.idea/
```

## 2.2 Verified Dependencies (requirements.txt)

| Category | Dependencies | Version |
|----------|--------------|---------|
| **Web Server** | fastapi, uvicorn[standard], python-multipart | >=0.110.0 |
| **Environment** | python-dotenv | >=1.0.0 |
| **ML/Inference** | ultralytics, opencv-python-headless, torch, torchvision, transformers | latest |
| **PDF Processing** | pdfplumber, fpdf2, pymupdf | >=0.11.0 |
| **Utilities** | matplotlib, pandas, scikit-image, numpy, Pillow | >=2.0.0 |
| **External APIs** | requests, httpx | >=2.31.0 |
| **Security** | cryptography | >=42.0.0 |

**Verified via:** `grep -r "import\|from" Model_Backend/*.py` → All imports have matching requirements.txt entries

## 2.3 Security Hardening Implementation

### Environment Variables Configuration

#### Backend (.env.example)
```env
# Supabase Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Encryption (Fernet 32-byte base64)
ENCRYPTION_KEY=your_fernet_32byte_base64_key

# Pinata IPFS
PINATA_JWT=your_pinata_jwt_token
PINATA_GATEWAY_URL=https://gateway.pinata.cloud/ipfs

# Model Paths
MODEL_PATH=model/best.pt
GRADCAM_MODEL_PATH=gradcam.pt
SHAP_MODEL_PATH=shap.pt
SSIM_MODEL_PATH=ssim.pt

# CORS Security (production domains only)
ALLOWED_ORIGINS=http://localhost:5173,https://pixel-app.vercel.app

# Feature Flags
ENABLE_ZERO_SHOT=1
```

#### Frontend (.env.example)
```env
VITE_API_BASE_URL=https://pixel-api.up.railway.app
VITE_API_PROXY_TARGET=http://localhost:8000  # Dev only
```

### CORS Security Configuration

| Environment | Allowed Origins |
|-------------|-----------------|
| **Development** | `http://localhost:5173` |
| **Production** | `https://pixel-app.vercel.app` |
| **Blocked** | `*` (wildcards rejected) |

**Implementation in main.py:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Secret Rotation Requirements

| Service | Action | When |
|---------|--------|------|
| **Supabase** | Regenerate anon key | If ever committed to Git |
| **Pinata** | Generate new JWT | If ever committed to Git |
| **Encryption** | Create new Fernet key | If ever committed to Git |

**Generate new Fernet key:**
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()  # URL-safe base64-encoded
```

## 2.4 Security Verification Results

| Check | Method | Result |
|-------|--------|--------|
| Hardcoded secrets search | `grep -r "SUPABASE_KEY\|PINATA_JWT" Model_Backend/*.py` | ✅ None found |
| .env in .gitignore | Check `.gitignore` line 14 | ✅ Confirmed |
| Model files excluded | Check `.gitignore` lines 25-29 | ✅ Confirmed |
| Example templates exist | Check `.env.example` files | ✅ Both present |
| CORS configured | Check `main.py` CORS middleware | ✅ Env-based |

## 2.5 Why Security Matters

| Risk | Prevention | Impact of Failure |
|------|------------|-------------------|
| **Credential Leaks** | .gitignore + .env.example | Database breach, IPFS abuse |
| **Model Theft** | Gitignore .pt files | IP theft, competitive loss |
| **CORS Attacks** | Restricted origins | Unauthorized API access |
| **Audit Tampering** | Encrypted logs | Compliance violations |
| **Supply Chain** | Pinned dependencies | Malicious package injection |

---

# Slide 3: Backend Deployment (Docker + Railway)

## 3.1 Containerization Strategy

### Dockerfile Structure

| Stage | Instruction | Purpose |
|-------|-------------|---------|
| **Base** | `FROM python:3.11-slim` | Minimal Python image |
| **System Deps** | `apt-get install libgl1, libglib2.0-0` | OpenCV system libraries |
| **Python Deps** | `COPY requirements.txt` | Dependency layer caching |
| **Torch Install** | `pip install torch --index-url cpu` | CPU-only (saves 1.5GB) |
| **App Code** | `COPY . .` | Application files |
| **Runtime Dirs** | `mkdir -p /app/outputs, /app/audit_logs` | Writable directories |
| **Port** | `EXPOSE 8000` | Container port |
| **Health Check** | `HEALTHCHECK curl /api/health` | Container health monitoring |
| **Start** | `CMD uvicorn main:app --host 0.0.0.0` | Production server |

### Multi-Stage Build Benefits
- **Layer Caching**: requirements.txt changes rarely → fast rebuilds
- **Smaller Image**: CPU-only torch saves ~1.5GB vs CUDA version
- **Security**: Slim base image reduces attack surface
- **Health Monitoring**: Built-in health check for orchestration

## 3.2 Model Handling Options

### Option A: Railway Volume (RECOMMENDED)

| Aspect | Configuration |
|--------|---------------|
| **Mount Path** | `/app/model` |
| **Upload Method** | Railway CLI or Dashboard |
| **Persistence** | Survives container restarts |
| **Size Limit** | Up to 100GB per volume |
| **Cost** | $0.25/GB/month |

**Steps:**
1. Create Volume in Railway Dashboard
2. Attach to service
3. Upload model files via Railway CLI:
   ```bash
   railway volumes upload model/best.pt /app/model/best.pt
   ```

### Option B: Download at Startup

| Aspect | Configuration |
|--------|---------------|
| **Source** | HuggingFace, S3, or custom URL |
| **Implementation** | Add to Dockerfile or startup script |
| **Pros** | No manual upload needed |
| **Cons** | Slower cold start, bandwidth costs |

**Example startup script:**
```bash
# Download models if not present
if [ ! -f "/app/model/best.pt" ]; then
    wget -O /app/model/best.pt https://your-cdn.com/best.pt
fi
```

## 3.3 Railway Configuration (railway.toml)

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "./Dockerfile"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
healthcheckPath = "/api/health"
healthcheckTimeout = 120
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 5
```

| Setting | Value | Purpose |
|---------|-------|---------|
| **Builder** | DOCKERFILE | Use provided Dockerfile |
| **Start Command** | uvicorn with dynamic port | Production ASGI server |
| **Healthcheck** | `/api/health` | Container health verification |
| **Timeout** | 120s | Allow ML model loading time |
| **Restart Policy** | ON_FAILURE, max 5 | Auto-recovery from crashes |

## 3.4 Deployment Steps

### Step 1: Railway CLI Setup
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link
```

### Step 2: Create Service
```bash
# Create new service from GitHub
railway service create

# Select repository and branch
railway service update --source github
```

### Step 3: Configure Environment Variables

| Variable | Source | Value |
|----------|--------|-------|
| `SUPABASE_URL` | Supabase Dashboard | `https://xxxx.supabase.co` |
| `SUPABASE_KEY` | Supabase Dashboard | `anon_key` |
| `ENCRYPTION_KEY` | Generated locally | `Fernet.generate_key()` |
| `PINATA_JWT` | Pinata Dashboard | JWT token |
| `ALLOWED_ORIGINS` | Your Vercel URL | `https://pixel-app.vercel.app` |
| `MODEL_PATH` | Default | `model/best.pt` |
| `GRADCAM_MODEL_PATH` | Default | `gradcam.pt` |
| `SHAP_MODEL_PATH` | Default | `shap.pt` |
| `SSIM_MODEL_PATH` | Default | `ssim.pt` |

**Add via CLI:**
```bash
railway variables set SUPABASE_URL="https://xxxx.supabase.co"
```

### Step 4: Attach Volume (for models)
```bash
# Create volume
railway volume create

# Attach to service
railway service update --volume my-volume:/app/model
```

### Step 5: Deploy
```bash
# Trigger deployment
railway up

# Monitor logs
railway logs
```

## 3.5 Expected Deployment Output

### Health Check Verification
```bash
$ curl https://pixel-api.up.railway.app/api/health

{
    "status": "ok",
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0"
}
```

### Service Information
| Property | Value |
|----------|-------|
| **Public URL** | `https://pixel-api.up.railway.app` |
| **Health Endpoint** | `GET /api/health` |
| **API Base** | `https://pixel-api.up.railway.app/api` |
| **Status** | 🟢 Healthy |
| **Region** | us-west (or your selected region) |

---

# Slide 4: Frontend Deployment & Integration

## 4.1 Vercel Deployment Configuration

### Project Structure
```
Frontend/
├── src/              # React source code
├── public/           # Static assets
├── dist/             # Build output (generated)
├── package.json      # Dependencies
├── vite.config.js    # Vite configuration
└── index.html        # Entry HTML
```

### Build Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| **Framework Preset** | Vite | Auto-detected |
| **Root Directory** | `Frontend` | Monorepo subfolder |
| **Build Command** | `npm install && npm run build` | Dependency install + build |
| **Output Directory** | `dist` | Vite default output |
| **Install Command** | `npm install` | Node modules |

## 4.2 Environment Variable Setup

### Production Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `VITE_API_BASE_URL` | `https://pixel-api.up.railway.app` | Backend API endpoint |

### Development vs Production

| Environment | VITE_API_BASE_URL | Behavior |
|-------------|-------------------|----------|
| **Local Dev** | `http://localhost:8000` | Proxy via Vite dev server |
| **Production** | `https://pixel-api.up.railway.app` | Direct API calls |

### Configuration in Code
```typescript
// Frontend API client
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export const apiClient = {
    analyze: async (image: File) => {
        const formData = new FormData();
        formData.append('image', image);
        
        const response = await fetch(`${API_BASE}/api/analyze`, {
            method: 'POST',
            body: formData,
        });
        return response.json();
    }
};
```

## 4.3 Vercel Deployment Steps

### Method A: Vercel CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy (from Frontend directory)
cd Frontend
vercel --prod

# Set environment variable
vercel env add VITE_API_BASE_URL production
```

### Method B: Git Integration (RECOMMENDED)

1. **Connect Repository**
   - Go to [vercel.com](https://vercel.com)
   - Click "Add New Project"
   - Import from GitHub

2. **Configure Project**
   | Setting | Value |
   |---------|-------|
   | Framework | Vite |
   | Root Directory | `Frontend` |
   | Build Command | `npm run build` |
   | Output Directory | `dist` |

3. **Environment Variables**
   - Add `VITE_API_BASE_URL`
   - Value: `https://pixel-api.up.railway.app`
   - Target: Production

4. **Deploy**
   - Click "Deploy"
   - Auto-builds on every git push

## 4.4 Frontend-Backend Integration Flow

### Complete Request Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER ACTION: Upload X-ray                        │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. FRONTEND: React Component handles file selection                     │
│    - Drag & drop or file picker                                        │
│    - Client-side validation (type, size)                               │
│    - Show loading state                                                │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         │ POST /api/analyze
                                         │ (multipart/form-data)
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. BACKEND: FastAPI receives request                                  │
│    - CORS validation (origin check)                                    │
│    - File upload handling                                              │
│    - Trigger ML pipeline                                               │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         │ Inference
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. ML PIPELINE: YOLO→GradCAM→SHAP processing                           │
│    - Load model from Railway Volume                                    │
│    - Run detection on X-ray image                                      │
│    - Generate segmentation masks                                       │
│    - Classify contraband items                                         │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         │ Store results
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. DATABASE: Supabase operations                                       │
│    - Insert detection record                                           │
│    - Update shipment manifest                                            │
│    - Encrypt sensitive data                                              │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         │ Log audit
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. STORAGE: Pinata IPFS logging                                       │
│    - Create audit log entry                                            │
│    - Encrypt log content                                               │
│    - Pin to IPFS                                                       │
│    - Store CID in database                                             │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         │ JSON Response
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. FRONTEND: Display results                                          │
│    - Render detection bounding boxes                                   │
│    - Show contraband classification                                    │
│    - Display confidence scores                                         │
│    - Enable report export                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

## 4.5 CORS Configuration for Production

### Backend CORS Settings
```python
# Model_Backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://pixel-app.vercel.app",  # Production frontend
        "http://localhost:5173",          # Local development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Environment Variable
```env
ALLOWED_ORIGINS=https://pixel-app.vercel.app,http://localhost:5173
```

### CORS Security Rules
| Rule | Implementation |
|------|----------------|
| **No wildcards in production** | Explicit origin list only |
| **Allow credentials** | For authenticated requests |
| **Restrict methods** | GET, POST only for public |
| **Vary header** | Automatic by FastAPI |

## 4.6 Integration Verification

### End-to-End Test
```bash
# 1. Frontend loads
curl -I https://pixel-app.vercel.app
# HTTP/2 200 OK

# 2. API health check passes
curl https://pixel-api.up.railway.app/api/health
# {"status":"ok"}

# 3. CORS preflight succeeds
curl -X OPTIONS \
  -H "Origin: https://pixel-app.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  https://pixel-api.up.railway.app/api/analyze
# 200 OK with CORS headers

# 4. File upload works
# (Test via browser - upload X-ray, get detection results)
```

### Expected Final State
| Component | Status | URL |
|-----------|--------|-----|
| **Frontend** | 🟢 Live | `https://pixel-app.vercel.app` |
| **Backend** | 🟢 Healthy | `https://pixel-api.up.railway.app` |
| **Database** | 🟢 Connected | Supabase |
| **Storage** | 🟢 Active | Pinata |
| **Integration** | 🟢 Working | Full pipeline operational |

---

# Slide 5: Testing, Verification & Final Workflow

## 5.1 Complete Deployment Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: PRE-DEPLOYMENT PREPARATION                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ Clean Repo  │→│ Verify Env  │→│ Test Local  │→│ Build Docker│      │
│  │ Remove .env │  │ Files Exist │  │ Docker Run  │  │ Image       │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: BACKEND DEPLOYMENT (RAILWAY)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ Connect Git │→│ Configure   │→│ Add Env     │→│ Deploy &    │      │
│  │ Repository  │  │ Docker Build│  │ Variables   │  │ Monitor     │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 3: FRONTEND DEPLOYMENT (VERCEL)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ Import Repo │→│ Set Build   │→│ Configure   │→│ Deploy to   │      │
│  │ to Vercel   │  │ Settings    │  │ API URL     │  │ Production  │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 4: INTEGRATION & TESTING                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ CORS Config │→│ Health Check│→│ E2E Upload  │→│ Verify      │      │
│  │ Update Origins│ │ Test API    │  │ Test        │  │ Database    │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

## 5.2 Testing Checklist

### API Health Check
| Test | Command | Expected Result |
|------|---------|-----------------|
| **Basic Health** | `curl /api/health` | `{"status":"ok"}` |
| **Full Status** | `curl /api/health/detailed` | System metrics |
| **CORS Preflight** | `curl -X OPTIONS` | 200 + CORS headers |

### End-to-End Upload Test
| Step | Action | Verification |
|------|--------|--------------|
| 1 | Navigate to Vercel frontend | Page loads, no console errors |
| 2 | Upload test X-ray image | Progress indicator shows |
| 3 | Wait for processing | Spinner/loading state |
| 4 | View detection results | Bounding boxes rendered |
| 5 | Check confidence scores | Values 0.0 - 1.0 displayed |
| 6 | Export report | PDF/JSON download works |

### Database Validation (Supabase)
```sql
-- Verify data insertion
SELECT COUNT(*) FROM xray_detections 
WHERE created_at > NOW() - INTERVAL '1 hour';
-- Should return > 0 after test upload

-- Verify encryption
SELECT shipment_id, LENGTH(encrypted_data) 
FROM shipments LIMIT 1;
-- encrypted_data should be non-null
```

### IPFS Audit Log Verification
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Perform detection | Upload + analyze |
| 2 | Query database | Get `audit_cid` from record |
| 3 | Access IPFS | `https://gateway.pinata.cloud/ipfs/{cid}` |
| 4 | Verify content | Decrypt and check log structure |

## 5.3 Integration Validation Matrix

| Integration | Test Method | Success Criteria |
|-------------|-------------|------------------|
| **Frontend ↔ Backend** | Browser DevTools Network tab | 200 OK, no CORS errors |
| **Backend ↔ Supabase** | Backend logs | "Connected to Supabase" message |
| **Backend ↔ Pinata** | IPFS gateway access | CID resolves to content |
| **ML Models** | Inference timing | < 5 seconds for standard image |
| **Encryption** | Database query | Data stored as encrypted blob |

## 5.4 Final System Verification

### Production URLs
| Service | URL | Status |
|---------|-----|--------|
| **Frontend** | `https://pixel-app.vercel.app` | ✅ Accessible |
| **Backend API** | `https://pixel-api.up.railway.app` | ✅ Healthy |
| **Health Check** | `https://pixel-api.up.railway.app/api/health` | ✅ Responding |
| **Documentation** | `https://pixel-api.up.railway.app/docs` | ✅ Swagger UI |

### Performance Benchmarks
| Metric | Target | Verification |
|--------|--------|--------------|
| **API Response Time** | < 200ms (health) | `curl -w "%{time_total}"` |
| **Image Processing** | < 10 seconds | Stopwatch test |
| **Frontend Load** | < 3 seconds | Lighthouse audit |
| **Uptime** | 99.9% | Railway/Vercel dashboards |

## 5.5 Final Outcome Summary

### ✅ Fully Deployed AI Platform

| Feature | Status |
|---------|--------|
| **Frontend** | React app live on Vercel CDN |
| **Backend** | FastAPI container running on Railway |
| **ML Models** | YOLOv8 + SAM operational |
| **Database** | PostgreSQL on Supabase with RLS |
| **Audit Trail** | Encrypted logs on IPFS via Pinata |
| **Security** | CORS restricted, secrets in env vars |
| **Scalability** | Auto-scaling enabled on both platforms |

### 🎯 Production-Ready Characteristics

1. **Reliability**: Health checks, auto-restart, crash recovery
2. **Security**: End-to-end encryption, CORS protection, secret management
3. **Performance**: Global CDN, optimized Docker image, model caching
4. **Observability**: Structured logging, audit trails, monitoring dashboards
5. **Compliance**: Tamper-proof audit logs via IPFS, encrypted data at rest

### 📊 Cost Summary (Monthly Estimates)

| Service | Tier | Cost |
|---------|------|------|
| **Vercel** | Pro (1TB bandwidth) | $20 |
| **Railway** | Starter + 10GB volume | $15 |
| **Supabase** | Pro (8GB database) | $25 |
| **Pinata** | Dedicated Gateway | $20 |
| **Total** | | **~$80/month** |

> **Note**: Free tiers available for development (Vercel hobby, Railway $5 credit, Supabase 500MB)

---

## Appendix: Quick Reference Commands

### Railway CLI
```bash
railway login                    # Authenticate
railway link                   # Link to project
railway up                     # Deploy
railway logs                   # View logs
railway variables set KEY=VAL  # Set env var
railway status                 # Check status
```

### Vercel CLI
```bash
vercel login                   # Authenticate
vercel --prod                  # Deploy to production
vercel env add KEY             # Add env var
vercel logs                    # View logs
```

### Docker Local Testing
```bash
cd Model_Backend
docker build -t pixel-backend .
docker run -p 8000:8000 --env-file .env pixel-backend
curl http://localhost:8000/api/health
```

---

**End of Presentation Slides**
