"""
Detection service — YOLOv8 wrapper, optimised for Intel i3 CPU + UHD graphics.

Optimisations applied:
  • imgsz=320   — half the default; 4× fewer pixels → ~2× faster on CPU
  • device=cpu  — never attempts GPU (no discrete VRAM)
  • half=False  — FP16 is GPU-only; CPU needs FP32
  • workers=0   — avoids forking overhead on low-core CPUs
  • threads     — capped via INFERENCE_THREADS env var (default 2 of 4)
  • image cap   — frames are downscaled to YOLO_MAX_DIM before inference;
                  original bbox coords are scaled back up

OpenVINO path (recommended for best i3 perf):
  Run `python scripts/export_openvino.py` once to export the model.
  Set FRESHVISION_YOLO_WEIGHTS=yolov8n_openvino/yolov8n.xml in .env.
  Ultralytics transparently uses OpenVINO runtime for ~30% speedup on Intel.
"""
import logging
import threading
import uuid
from typing import List, Tuple

import cv2
import numpy as np

from app.core.config import (
    YOLO_WEIGHTS, YOLO_CONF_THRESHOLD, YOLO_IMGSZ,
    YOLO_DEVICE, YOLO_MAX_DIM, INFERENCE_THREADS, PRODUCE_COCO_CLASSES,
)

logger = logging.getLogger("freshvision.detection")

# Global model + lock (one model instance, serialised inference — safe for
# multi-worker uvicorn because each worker process gets its own copy)
_model      = None
_model_lock = threading.Lock()
_load_failed = False


def _get_model():
    global _model, _load_failed
    if _model is not None or _load_failed:
        return _model
    with _model_lock:
        if _model is not None or _load_failed:
            return _model
        try:
            # Limit OpenBLAS / OpenMP threads so we don't starve uvicorn workers
            import os
            os.environ.setdefault("OMP_NUM_THREADS",      str(INFERENCE_THREADS))
            os.environ.setdefault("OPENBLAS_NUM_THREADS", str(INFERENCE_THREADS))
            os.environ.setdefault("MKL_NUM_THREADS",      str(INFERENCE_THREADS))

            from ultralytics import YOLO
            _model = YOLO(YOLO_WEIGHTS)
            logger.info("Loaded model: %s  device=%s  imgsz=%d", YOLO_WEIGHTS, YOLO_DEVICE, YOLO_IMGSZ)
        except Exception as exc:
            logger.warning("YOLO load failed (%s) — whole-frame fallback active.", exc)
            _load_failed = True
    return _model


def _cap_image(image_bgr: np.ndarray) -> Tuple[np.ndarray, float]:
    """Downscale to YOLO_MAX_DIM on longest edge; return (image, scale)."""
    h, w = image_bgr.shape[:2]
    longest = max(h, w)
    if longest <= YOLO_MAX_DIM:
        return image_bgr, 1.0
    scale = YOLO_MAX_DIM / longest
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(image_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, scale


class Detection:
    def __init__(self, product_type: str, confidence: float,
                 bbox: Tuple[int, int, int, int]):
        self.item_id      = uuid.uuid4().hex[:8]
        self.product_type = product_type
        self.confidence   = confidence
        self.bbox         = bbox   # (x, y, w, h) in original image coords


def detect_produce(image_bgr: np.ndarray) -> List[Detection]:
    """
    Detect produce items and return a Detection per item.

    Falls back to treating the whole frame as one item if YOLO weights
    cannot be loaded (offline environment, restricted network, etc.).
    """
    h, w = image_bgr.shape[:2]
    model = _get_model()

    if model is None:
        return [Detection("produce_item", 0.50, (0, 0, w, h))]

    small, scale = _cap_image(image_bgr)

    with _model_lock:
        results = model.predict(
            small,
            imgsz=YOLO_IMGSZ,
            conf=YOLO_CONF_THRESHOLD,
            device=YOLO_DEVICE,
            half=False,         # no FP16 on CPU
            workers=0,          # no DataLoader workers
            verbose=False,
        )

    detections: List[Detection] = []
    for r in results:
        names = r.names
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label  = names[cls_id] if isinstance(names, (list,)) else names.get(cls_id, str(cls_id))
            if label.lower() not in PRODUCE_COCO_CLASSES:
                continue
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            # Scale coordinates back to original image space
            x1 = int(x1 / scale); y1 = int(y1 / scale)
            x2 = int(x2 / scale); y2 = int(y2 / scale)
            detections.append(Detection(label.lower(), conf, (x1, y1, x2 - x1, y2 - y1)))

    if not detections:
        detections.append(Detection("unidentified_produce", 0.40, (0, 0, w, h)))

    return detections
