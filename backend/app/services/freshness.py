"""
Freshness + shelf-life prediction.

Freshness score combines:
  - visual defect coverage (from defect_analysis)
  - color-fade signal: saturation drop vs. a "fresh" reference range is a
    well-documented ripeness/senescence cue for produce
  - texture dulling: fresh produce has more high-frequency surface detail
    (skin texture, sheen) than wilted/shriveled produce

Shelf-life estimate blends the freshness score with storage conditions
(temperature/humidity) using a simple decay heuristic. This is intentionally
transparent rather than a black-box regressor, in line with the explainable
AI requirement; the README documents how to replace it with an XGBoost
model trained on real inspection-history data once it exists.
"""
import cv2
import numpy as np

from app.core.config import FRESHNESS_BANDS


def _texture_sharpness(crop_bgr: np.ndarray, mask: np.ndarray) -> float:
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    if np.count_nonzero(mask) == 0:
        return float(np.var(lap))
    return float(np.var(lap[mask > 0]))


def predict_freshness(crop_bgr: np.ndarray, mask: np.ndarray, defect_coverage_pct: float):
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    sat_vals = hsv[:, :, 1][mask > 0]
    saturation = float(np.mean(sat_vals)) if sat_vals.size else 0.0

    sharpness = _texture_sharpness(crop_bgr, mask)
    # Normalize sharpness against a generous reference ceiling (empirically
    # tuned on typical phone/webcam produce photos, not a hard physical law).
    sharpness_score = min(sharpness / 350.0, 1.0)
    saturation_score = min(saturation / 140.0, 1.0)
    defect_penalty = min(defect_coverage_pct * 1.8, 1.0)

    freshness_pct = 100 * (
        0.45 * saturation_score + 0.30 * sharpness_score + 0.25 * (1 - defect_penalty)
    )
    freshness_pct = max(0.0, min(100.0, round(freshness_pct, 1)))

    label = "Spoiled"
    for low, high, name in FRESHNESS_BANDS:
        if low <= freshness_pct <= high:
            label = name
            break

    confidence = round(0.55 + 0.35 * (1 - abs(freshness_pct - 50) / 50), 2)
    return label, freshness_pct, min(confidence, 0.95)


def predict_shelf_life(freshness_pct: float, storage_temp_c: float = 6.0, storage_humidity_pct: float = 85.0):
    """
    Heuristic decay model:
      base_days = how many days of shelf life a "100% fresh" item of this
                  general category would have at ideal cold-chain conditions
      temp_penalty   -- shelf life roughly halves per +8C above 4C (cold chain)
      humidity_penalty -- very low humidity accelerates dehydration/shrinkage
    """
    base_days = 10.0 * (freshness_pct / 100.0) ** 1.3

    temp_excess = max(storage_temp_c - 4.0, 0.0)
    temp_factor = 0.5 ** (temp_excess / 8.0)

    humidity_factor = 1.0
    if storage_humidity_pct < 80:
        humidity_factor = max(0.6, storage_humidity_pct / 80.0)

    remaining_days = round(max(base_days * temp_factor * humidity_factor, 0.0), 1)
    confidence = 0.6 if (4 <= storage_temp_c <= 10 and 70 <= storage_humidity_pct <= 95) else 0.45

    if remaining_days <= 0.5:
        action = "Immediate sale or disposal"
    elif remaining_days <= 1.5:
        action = "Priority dispatch / quick sale today"
    elif remaining_days <= 3:
        action = "Move to front-of-shelf, monitor daily"
    else:
        action = "Standard rotation"

    return remaining_days, confidence, action
