"""
FreshVision AI — Central Configuration
All tunables in one place. Override via environment variables.
"""
import os
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = Path(os.getenv("FRESHVISION_STORAGE_DIR", str(BASE_DIR / "storage")))
UPLOAD_DIR  = STORAGE_DIR / "uploads"
OVERLAY_DIR = STORAGE_DIR / "overlays"
LOG_DIR     = STORAGE_DIR / "logs"
DB_PATH     = Path(os.getenv("FRESHVISION_DB_PATH", str(STORAGE_DIR / "freshvision.db")))

for _d in (UPLOAD_DIR, OVERLAY_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Auth ────────────────────────────────────────────────────────────────────
JWT_SECRET          = os.getenv("FRESHVISION_JWT_SECRET", "CHANGE-ME-IN-PRODUCTION")
JWT_ALGORITHM       = "HS256"
JWT_EXPIRE_MINUTES  = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))   # 12 h
REFRESH_EXPIRE_DAYS = int(os.getenv("REFRESH_EXPIRE_DAYS", "7"))

# Self-service sign-up. Each new account gets its own private data — no
# inspection, history, or analytics is ever shared between users (except the
# 'admin' role, which can see everything for support/oversight purposes).
ALLOW_REGISTRATION = os.getenv("ALLOW_REGISTRATION", "true").lower() == "true"
DEFAULT_USER_ROLE   = os.getenv("DEFAULT_USER_ROLE", "inspector")

# Seed the two built-in demo accounts (admin/inspector) on first boot.
# Turn this OFF for any real deployment — set SEED_DEMO_USERS=false and
# register your own account instead, or the well-known demo password will
# work against your instance.
SEED_DEMO_USERS = os.getenv("SEED_DEMO_USERS", "true").lower() == "true"

# Startup will refuse to run with the default JWT secret once this is on
# (auto-enabled when ENVIRONMENT=production).
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

# ── Upload limits ───────────────────────────────────────────────────────────
MAX_UPLOAD_BYTES    = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))  # 10 MB
ALLOWED_MIME_TYPES  = {"image/jpeg", "image/png", "image/webp"}

# ── Rate limiting ───────────────────────────────────────────────────────────
RATE_LIMIT_INSPECT  = os.getenv("RATE_LIMIT_INSPECT", "30/minute")
RATE_LIMIT_DEFAULT  = os.getenv("RATE_LIMIT_DEFAULT", "120/minute")

# ── Detection (Intel CPU optimised) ────────────────────────────────────────
# Weights: yolov8n.pt   ← smallest, fastest, ~6 MB, good for i3 CPU
# To use OpenVINO-accelerated IR model instead:
#   python scripts/export_openvino.py          → creates yolov8n_openvino/
#   set FRESHVISION_YOLO_WEIGHTS=yolov8n_openvino/yolov8n.xml
YOLO_WEIGHTS          = os.getenv("FRESHVISION_YOLO_WEIGHTS", "yolov8n.pt")
YOLO_CONF_THRESHOLD   = float(os.getenv("YOLO_CONF_THRESHOLD", "0.35"))
YOLO_IMGSZ            = int(os.getenv("YOLO_IMGSZ", "320"))          # 320 for i3 speed
YOLO_DEVICE           = os.getenv("YOLO_DEVICE", "cpu")              # always CPU here
YOLO_MAX_DIM          = int(os.getenv("YOLO_MAX_DIM", "960"))        # resize before inference
INFERENCE_THREADS     = int(os.getenv("INFERENCE_THREADS", "2"))     # i3 = 4 threads total

# COCO classes that count as produce
PRODUCE_COCO_CLASSES = {
    "apple","banana","orange","broccoli","carrot",
    "hot dog","pizza","donut","cake",               # fallback demo classes
}

# ── Defect analysis ─────────────────────────────────────────────────────────
DARK_SPOT_THRESH    = int(os.getenv("DARK_SPOT_THRESH", "60"))
SPOT_MIN_AREA_RATIO = float(os.getenv("SPOT_MIN_AREA_RATIO", "0.0015"))

# ── Quality grading (weighted defect coverage → grade) ─────────────────────
GRADE_THRESHOLDS = {
    "Premium": 0.01,
    "Grade A": 0.04,
    "Grade B": 0.10,
    "Grade C": 0.22,
    # above 0.22 → Reject
}

# ── Freshness bands (0-100 score → label) ──────────────────────────────────
FRESHNESS_BANDS = [
    (85, 100, "Fresh"),
    (65,  85, "Good"),
    (45,  65, "Needs Quick Sale"),
    (25,  45, "Near Expiry"),
    (0,   25, "Spoiled"),
]

# ── Decision engine ─────────────────────────────────────────────────────────
COLD_CHAIN_PRODUCTS = {"egg"}

# ── CORS ────────────────────────────────────────────────────────────────────
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost,http://localhost:80,http://localhost:5173,http://localhost:3000"
).split(",")
