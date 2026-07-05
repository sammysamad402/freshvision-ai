# ── FreshVision AI — Backend Dockerfile ─────────────────────────────────────
# Optimised for Intel i3 / UHD integrated graphics (CPU-only inference)
FROM python:3.11-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 curl \
    && rm -rf /var/lib/apt/lists/*

FROM base AS deps
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

FROM deps AS model
RUN python -c "
import os; os.environ['OMP_NUM_THREADS']='1'
from ultralytics import YOLO; YOLO('yolov8n.pt')
print('Weights cached.')
" 2>/dev/null || echo "Offline build — weights will download at runtime."

FROM model AS app
WORKDIR /app
RUN groupadd -r freshvision && useradd -r -g freshvision -d /app -s /sbin/nologin freshvision
COPY --chown=freshvision:freshvision . .
RUN mkdir -p /data/uploads /data/overlays /data/logs \
 && chown -R freshvision:freshvision /data \
 && (chown -R freshvision:freshvision /root/.config 2>/dev/null || true)

ENV FRESHVISION_STORAGE_DIR=/data \
    FRESHVISION_DB_PATH=/data/freshvision.db \
    OMP_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2 \
    MKL_NUM_THREADS=2

USER freshvision
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1","--loop","asyncio","--access-log"]
