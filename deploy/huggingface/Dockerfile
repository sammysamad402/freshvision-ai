# ── FreshVision AI — Hugging Face Spaces Dockerfile ────────────────────────
#
# HF Spaces requirements:
#   • App must listen on port 7860
#   • Must run as user with uid 1000 (HF enforces this)
#   • No sudo, no root at runtime
#
# Free tier specs: 2 vCPU · 16 GB RAM  ← YOLOv8n runs great here

FROM python:3.11-slim

# System deps for OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 curl \
    && rm -rf /var/lib/apt/lists/*

# Create HF-compatible user (uid=1000 is required by HF Spaces)
RUN useradd -m -u 1000 -s /bin/bash user

WORKDIR /home/user/app

# Install Python deps as root first (faster layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Pre-download YOLO weights at build time (so first inference isn't slow)
# HF has internet during build; weights are baked into the image layer
RUN python -c "
import os
os.environ['OMP_NUM_THREADS'] = '1'
from ultralytics import YOLO
YOLO('yolov8n.pt')
print('YOLOv8n weights cached in image.')
" 2>/dev/null || echo "Weight download skipped — will download at runtime."

# Copy app code
COPY --chown=user:user . .

# Storage lives in /home/user/data (ephemeral on HF free tier)
# Images & overlays are uploaded to Supabase Storage, so local disk is only
# used as a temporary buffer — no data is lost if the Space restarts.
RUN mkdir -p /home/user/data/uploads /home/user/data/overlays /home/user/data/logs \
 && chown -R user:user /home/user/data

# Switch to non-root user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    FRESHVISION_STORAGE_DIR=/home/user/data \
    FRESHVISION_DB_PATH=/home/user/data/freshvision.db \
    OMP_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    YOLO_DEVICE=cpu \
    YOLO_IMGSZ=320

# HF Spaces requires port 7860
EXPOSE 7860

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "7860", \
     "--workers", "1", \
     "--loop", "asyncio", \
     "--access-log"]
