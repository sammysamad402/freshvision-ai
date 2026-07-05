<div align="center">

# 🌿 FreshVision AI

### AI-Powered Automated Quality Inspection & Freshness Prediction

[![CI](https://github.com/YOUR_USERNAME/freshvision-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/freshvision-ai/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![HF Spaces](https://img.shields.io/badge/🤗-Hugging%20Face%20Spaces-yellow)](https://huggingface.co/spaces)

**Upload a produce photo → AI detects defects → grades quality → predicts freshness → makes warehouse decision. All free, all open source.**

</div>

---

## 🆓 Free Hosting Stack

```
GitHub (code)  →  Hugging Face Spaces (backend AI, 16GB RAM free)
               →  Vercel             (frontend, free forever)
               →  Supabase           (database + image storage, free)
```

> **Why Hugging Face instead of Railway?**
> HF Spaces free tier gives you **16 GB RAM** vs Railway's 512 MB.
> YOLOv8 needs ~350 MB to load — HF is the right tool for ML workloads.

---

## ⚡ Step-by-Step Hosting Guide

> **Time needed: ~20 minutes. No credit card anywhere.**

---

### 1️⃣ Fork this repo on GitHub

Click **Fork** (top right of this page) → then clone it:

```bash
git clone https://github.com/YOUR_USERNAME/freshvision-ai
cd freshvision-ai
```

Replace `YOUR_USERNAME` with your actual GitHub username everywhere below.

---

### 2️⃣ Set up Supabase (database + image storage)

> supabase.com — free, no credit card

**a)** Go to [supabase.com](https://supabase.com) → **Start your project** → sign up with GitHub

**b)** Click **New project** → name it `freshvision` → pick any region → **Create project** (takes ~2 min)

**c)** Go to **Settings → Database** → scroll to **Connection string** → select **URI** tab → copy it. Looks like:
```
postgresql://postgres:YOUR_PASSWORD@db.abcxyz.supabase.co:5432/postgres
```

**d)** Go to **Settings → API** → copy two things:
- **Project URL** (like `https://abcxyz.supabase.co`)
- **anon public** key (long string starting with `eyJ...`)

**e)** Go to **Storage** → **New bucket** → name: `freshvision` → tick ✅ **Public bucket** → **Create bucket**

Save those 3 values — you need them in the next steps. ✅

---

### 3️⃣ Deploy backend to Hugging Face Spaces

> huggingface.co — free, no credit card, 16GB RAM

**a)** Go to [huggingface.co](https://huggingface.co) → sign up → verify email

**b)** Click your profile picture → **New Space**

Fill in:
- **Space name:** `freshvision-backend`
- **License:** MIT
- **SDK:** Docker  ← important, pick Docker
- **Visibility:** Public

Click **Create Space**

**c)** You're now in your Space. Click the **Files** tab → you'll see it's empty.

**d)** On your computer, run:
```bash
# This builds a ready-to-push folder
bash scripts/build_hf_space.sh
```

**e)** Now push to your Space:
```bash
# Clone your HF Space (replace YOUR_HF_USERNAME)
git clone https://huggingface.co/spaces/YOUR_HF_USERNAME/freshvision-backend hf_deploy

# Copy the built files in
cp -r hf_space/. hf_deploy/

# Push
cd hf_deploy
git add .
git commit -m "initial deploy"
git push
```

> 💡 **If asked for password:** use your HF password, or better — create an access token at
> huggingface.co → Settings → Access Tokens → New token (write permission)
> and use that as the password.

**f)** The Space starts building — click **Logs** to watch. Build takes 3-5 min (downloads YOLO weights once, bakes them into the image).

**g)** Once it shows **Running**, click the **App** tab — or go to:
```
https://YOUR_HF_USERNAME-freshvision-backend.hf.space/health
```
You should see: `{"status":"ok","service":"FreshVision AI"}`

**h)** Go to **Settings → Variables** (in your Space) → add these:

| Name | Value |
|---|---|
| `FRESHVISION_JWT_SECRET` | Any long random text — e.g. `freshvision_secret_abc123xyz789` |
| `DATABASE_URL` | The PostgreSQL URI from Supabase step c |
| `SUPABASE_URL` | The Project URL from Supabase step d |
| `SUPABASE_KEY` | The anon key from Supabase step d |
| `CORS_ORIGINS` | `https://YOUR_VERCEL_URL.vercel.app,http://localhost` ← fill this after step 4 |

After adding variables → the Space restarts automatically. ✅

---

### 4️⃣ Deploy frontend to Vercel

> vercel.com — free forever, no credit card

**a)** Go to [vercel.com](https://vercel.com) → **Sign up** with GitHub

**b)** Click **Add New Project** → **Import** your `freshvision-ai` repo from GitHub

**c)** On the configuration screen:
- Set **Root Directory** to `frontend`
- Under **Environment Variables**, add:

| Name | Value |
|---|---|
| `VITE_API_URL` | `https://YOUR_HF_USERNAME-freshvision-backend.hf.space` |

**d)** Click **Deploy** → wait ~2 minutes → you get a URL like `https://freshvision-ai-abc123.vercel.app`

**e)** Go back to your **Hugging Face Space → Settings → Variables** → update `CORS_ORIGINS`:
```
https://freshvision-ai-abc123.vercel.app,http://localhost
```

Space restarts → done. ✅

---

### 5️⃣ Seed demo data (recommended for demos)

Your analytics dashboard will be empty until you run inspections. Seed 30 days of realistic data so judges see a full dashboard:

**Option A — from your computer:**
```bash
# Install deps locally first
cd backend
pip install -r requirements.txt

# Point at your live Supabase database
export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@db.abcxyz.supabase.co:5432/postgres"
export SUPABASE_URL="https://abcxyz.supabase.co"
export SUPABASE_KEY="eyJ..."

python -m scripts.seed_demo_data --days 30
```

**Option B — from HF Space terminal:**
In your Space page → click **⋮** menu → **Open in JupyterLab** (or use the terminal) → run:
```bash
python -m scripts.seed_demo_data --days 30
```

---

### 6️⃣ Set up auto-deploy (optional, takes 2 min)

Every time you push to `main`, GitHub Actions automatically redeploys to HF Spaces:

**a)** In your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**

Add two secrets:
- `HF_TOKEN` — your HF access token (from huggingface.co → Settings → Access Tokens)
- `HF_USERNAME` — your HF username

**b)** Vercel auto-deploys already — no setup needed (it listens to GitHub pushes automatically).

Now every `git push origin main` deploys everything. ✅

---

## 🌐 Your live URLs

After completing the steps above you'll have:

| What | URL |
|---|---|
| Dashboard | `https://freshvision-ai-xxx.vercel.app` |
| API | `https://YOUR_HF_USERNAME-freshvision-backend.hf.space` |
| API Docs | `https://YOUR_HF_USERNAME-freshvision-backend.hf.space/docs` |
| Health | `https://YOUR_HF_USERNAME-freshvision-backend.hf.space/health` |

**Login:** `admin` / `freshvision2024`

---

## 💻 Run locally (no cloud needed)

```bash
# Terminal 1 — backend (uses SQLite, no Supabase needed locally)
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# API at http://localhost:8000  |  Docs at http://localhost:8000/docs

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
# Dashboard at http://localhost:5173  |  Login: admin / freshvision2024

# Seed demo data (optional)
cd backend
python -m scripts.seed_demo_data --days 7
```

---

## 🧪 Tests

```bash
cd backend
python -m pytest tests/ -v
# 32 tests · ~3 seconds
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│  GitHub Actions CI                                        │
│  • Runs 32 tests on every push                           │
│  • Auto-deploys to HF Spaces + Vercel on merge to main   │
└───────────┬──────────────────────────────┬───────────────┘
            │                              │
            ▼                              ▼
┌───────────────────────┐    ┌─────────────────────────┐
│  Hugging Face Spaces  │    │  Vercel                  │
│  FastAPI + YOLOv8     │◀───│  React + TypeScript      │
│  16 GB RAM, 2 vCPU    │    │  Tailwind + Recharts     │
│  Free tier            │    │  Free forever            │
└───────────┬───────────┘    └─────────────────────────┘
            │
            ▼
┌───────────────────────┐
│  Supabase             │
│  PostgreSQL database  │
│  + Image storage      │
│  Free tier (500MB)    │
└───────────────────────┘
```

---

## 🤖 AI Pipeline

```
Image → YOLOv8 Detection → OpenCV Defect Analysis
→ Quality Grading (Premium/A/B/C/Reject)
→ Freshness Prediction (Fresh/Good/Needs Quick Sale/Near Expiry/Spoiled)
→ Shelf-Life Estimate (days at current temp/humidity)
→ Decision Engine (Accept/Reject/Priority Dispatch/Cold Storage/...)
→ Annotated Overlay + Explanation
```

---

## 🔧 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `FRESHVISION_JWT_SECRET` | ✅ | JWT signing key |
| `DATABASE_URL` | Production | Supabase PostgreSQL URI |
| `SUPABASE_URL` | Production | Supabase project URL |
| `SUPABASE_KEY` | Production | Supabase anon public key |
| `CORS_ORIGINS` | Production | Comma-separated allowed frontend origins |
| `YOLO_DEVICE` | No | `cpu` (always for free hosting) |
| `YOLO_IMGSZ` | No | `320` (fastest for free tier) |
| `LOG_LEVEL` | No | `INFO` |

---

## 📡 API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/login` | Login → JWT |
| GET | `/api/auth/me` | Current user |
| POST | `/api/inspect` | Run inspection on image |
| POST | `/api/inspect/batch` | Inspect up to 8 images |
| GET | `/api/inspect/history` | Inspection history |
| GET | `/api/inspect/{id}` | Inspection detail |
| GET | `/api/analytics/summary` | Dashboard KPIs |
| GET | `/api/analytics/export/csv` | CSV export |
| GET | `/health` | Health check |

---

## 🗺️ Roadmap

| Feature | Status |
|---|---|
| YOLOv8 produce detection | ✅ |
| OpenCV defect analysis (bruise, mold, rot, cracks) | ✅ |
| Quality grading 5-tier | ✅ |
| Freshness + shelf-life prediction | ✅ |
| Decision engine 6 outcomes | ✅ |
| JWT auth + RBAC | ✅ |
| Analytics dashboard + charts | ✅ |
| Batch inspection | ✅ |
| HF Spaces + Vercel + Supabase deploy | ✅ |
| GitHub Actions CI/CD | ✅ |
| 32 automated tests | ✅ |
| OpenVINO Intel acceleration | ✅ |
| Custom YOLO fine-tune on labelled produce | 📋 |
| SAM2 instance segmentation | 📋 |
| Live camera WebSocket stream | 📋 |
| PDF reports | 📋 |

---

## 🤝 Contributing

PRs welcome. Run `pytest tests/` before submitting.

## 📄 License

MIT — free to use, fork, and deploy.

---

<div align="center">
Built with FastAPI · React · YOLOv8 · OpenCV · Supabase · Hugging Face · Vercel
</div>
