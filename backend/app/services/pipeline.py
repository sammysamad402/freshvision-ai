"""
Pipeline orchestrator -- runs the full Image -> Detection -> Segmentation ->
Defects -> Grading -> Freshness -> Shelf-life -> Decision chain for a single
uploaded image and returns structured results + an annotated overlay image.
"""
import uuid
from datetime import datetime, timezone

import cv2
import numpy as np

from app.services.detection import detect_produce
from app.services.defect_analysis import analyze_defects
from app.services.grading import grade_product
from app.services.freshness import predict_freshness, predict_shelf_life
from app.services.decision_engine import decide
from app.services.explainability import draw_overlay


def run_inspection(image_bgr: np.ndarray, storage_temp_c: float = None, storage_humidity_pct: float = None):
    temp = storage_temp_c if storage_temp_c is not None else 6.0
    humidity = storage_humidity_pct if storage_humidity_pct is not None else 85.0

    detections = detect_produce(image_bgr)
    items_for_overlay = []
    result_items = []

    for det in detections:
        x, y, w, h = det.bbox
        x, y = max(0, x), max(0, y)
        w, h = max(1, min(w, image_bgr.shape[1] - x)), max(1, min(h, image_bgr.shape[0] - y))
        crop = image_bgr[y:y + h, x:x + w]

        anomalies, mask, coverage = analyze_defects(crop)
        grade, quality_score, grade_explanation = grade_product(anomalies, coverage)
        freshness_label, freshness_pct, freshness_conf = predict_freshness(crop, mask, coverage)
        shelf_days, shelf_conf, recommended_action = predict_shelf_life(
            freshness_pct, storage_temp_c=temp, storage_humidity_pct=humidity
        )
        decision, reasons = decide(det.product_type, grade, freshness_label, shelf_days, coverage)
        reasons.append(f"Shelf-life action: {recommended_action}")

        defect_dicts = [
            {"label": a.label, "confidence": a.confidence, "area_ratio": a.area_ratio, "bbox": list(a.bbox)}
            for a in anomalies
        ]

        explanation = (
            f"{det.product_type.title()} detected at {det.confidence*100:.0f}% confidence. "
            f"{grade_explanation} Freshness assessed as '{freshness_label}' "
            f"({freshness_pct:.1f}%) from color and surface-texture analysis. "
            f"Estimated {shelf_days} day(s) of remaining shelf life at {temp:.1f}\u00b0C / "
            f"{humidity:.0f}% RH. Decision: {decision} -- {reasons[0]}"
        )

        item = {
            "item_id": det.item_id,
            "product_type": det.product_type,
            "detection_confidence": round(det.confidence, 2),
            "bbox": [x, y, w, h],
            "defects": defect_dicts,
            "defect_coverage_pct": round(coverage * 100, 2),
            "quality_grade": grade,
            "quality_score": quality_score,
            "freshness_label": freshness_label,
            "freshness_pct": freshness_pct,
            "shelf_life_days": shelf_days,
            "shelf_life_confidence": shelf_conf,
            "decision": decision,
            "decision_reasons": reasons,
            "explanation": explanation,
        }
        result_items.append(item)
        items_for_overlay.append(item)

    overlay = draw_overlay(image_bgr, items_for_overlay)

    return {
        "inspection_id": uuid.uuid4().hex[:12],
        "timestamp": datetime.now(timezone.utc),
        "items": result_items,
        "storage_temp_c": temp,
        "storage_humidity_pct": humidity,
    }, overlay
