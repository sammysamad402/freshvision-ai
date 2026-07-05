"""
Defect analysis — classical computer vision (no training data required).

Why classical CV instead of a trained defect-segmentation net: there is no
freely redistributable pretrained model for "bruise/rot/mold on produce";
building one responsibly requires a labeled defect dataset we don't have.
Color- and texture-based blemish detection is a long-standing, legitimate
technique in produce QC (used in real packhouse sorting lines) and gives
genuinely explainable output today. The README documents how to swap this
module for a trained segmentation model (e.g. SAM2-assisted labeling -> a
fine-tuned UNet) once labeled defect imagery is available.

Pipeline per cropped product image:
  1. segment_produce_mask  -- isolate the product from its background
  2. find_anomalies        -- flag dark/bruised, discolored, and mold-like
                               regions inside that mask
  3. classify_anomaly      -- label each connected blob by its color/texture
"""
from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np

from app.core.config import DARK_SPOT_THRESH, SPOT_MIN_AREA_RATIO


@dataclass
class Anomaly:
    label: str
    confidence: float
    area_ratio: float
    bbox: Tuple[int, int, int, int]


def segment_produce_mask(crop_bgr: np.ndarray) -> np.ndarray:
    """Separate the product from background using saturation + Otsu value
    thresholding, then keep only the largest connected blob (the item)."""
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]

    # Background is usually a uniform tray/belt -- either near-white,
    # near-black, or low-saturation. Produce tends to be more saturated.
    _, sat_mask = cv2.threshold(s, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, val_mask = cv2.threshold(v, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    combined = cv2.bitwise_or(sat_mask, cv2.bitwise_not(val_mask))

    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(combined)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        cv2.drawContours(mask, [largest], -1, 255, thickness=cv2.FILLED)
    else:
        mask[:] = 255  # fall back to treating the whole crop as product
    return mask


def find_anomalies(crop_bgr: np.ndarray, produce_mask: np.ndarray) -> List[Anomaly]:
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    produce_area = int(np.count_nonzero(produce_mask))
    if produce_area == 0:
        return []

    # Dominant body color = median hue/sat/val inside the mask, used as the
    # "healthy tissue" baseline that everything else is compared against.
    body_h = float(np.median(h[produce_mask > 0]))
    body_s = float(np.median(s[produce_mask > 0]))
    body_v = float(np.median(v[produce_mask > 0]))

    # 1) Dark spots: bruising / rot / black spots -- value well below body baseline
    dark_thresh = max(DARK_SPOT_THRESH, body_v * 0.55)
    dark_mask = ((v < dark_thresh) & (produce_mask > 0)).astype(np.uint8) * 255

    # 2) Mold / fungus: desaturated, lighter-than-body fuzzy patches (whitish-grey/green)
    mold_mask = ((s < max(body_s * 0.45, 25)) & (v > body_v * 0.85) &
                 (produce_mask > 0)).astype(np.uint8) * 255

    # 3) Discoloration: hue far from body hue, but not dark or desaturated
    hue_dist = np.minimum(np.abs(h.astype(int) - int(body_h)), 180 - np.abs(h.astype(int) - int(body_h)))
    discolor_mask = ((hue_dist > 25) & (produce_mask > 0) &
                      (dark_mask == 0) & (mold_mask == 0)).astype(np.uint8) * 255

    anomalies: List[Anomaly] = []
    anomalies += _components_to_anomalies(dark_mask, produce_area, base_label="dark_spot")
    anomalies += _components_to_anomalies(mold_mask, produce_area, base_label="mold_fungus")
    anomalies += _components_to_anomalies(discolor_mask, produce_area, base_label="discoloration")

    # 4) Cracks / cuts: thin, high-edge-density structures detected via Canny
    edges = cv2.Canny(crop_bgr, 60, 160)
    edges = cv2.bitwise_and(edges, edges, mask=produce_mask)
    edges_dilated = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    anomalies += _components_to_anomalies(
        edges_dilated, produce_area, base_label="crack_or_cut",
        min_area_ratio=SPOT_MIN_AREA_RATIO * 1.5, elongation_filter=True, crop_for_shape=edges_dilated,
    )

    return anomalies


def _refine_label(base_label: str, crop_hsv_patch: np.ndarray) -> Tuple[str, float]:
    """Sharpen a generic bucket label using local color stats, with a
    confidence proportional to how strongly the patch matches the bucket."""
    if crop_hsv_patch.size == 0:
        return base_label, 0.5
    v_mean = float(np.mean(crop_hsv_patch[:, :, 2]))
    s_mean = float(np.mean(crop_hsv_patch[:, :, 1]))

    if base_label == "dark_spot":
        if v_mean < 35:
            return "black_spot", 0.85
        return "bruise_or_rot", 0.75
    if base_label == "mold_fungus":
        return "mold_fungus", 0.65 if s_mean < 20 else 0.55
    if base_label == "discoloration":
        return "discoloration", 0.6
    return base_label, 0.5


def _components_to_anomalies(
    mask: np.ndarray,
    produce_area: int,
    base_label: str,
    min_area_ratio: float = SPOT_MIN_AREA_RATIO,
    elongation_filter: bool = False,
    crop_for_shape: np.ndarray = None,
) -> List[Anomaly]:
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out: List[Anomaly] = []
    for c in contours:
        area = cv2.contourArea(c)
        ratio = area / produce_area if produce_area else 0
        if ratio < min_area_ratio:
            continue
        x, y, w, h = cv2.boundingRect(c)
        if elongation_filter:
            aspect = max(w, h) / max(min(w, h), 1)
            if aspect < 2.2:  # cracks/cuts are elongated; reject blobby matches
                continue
            label, conf = "crack_or_cut", min(0.5 + ratio * 8, 0.9)
        else:
            label, conf = base_label, min(0.5 + ratio * 6, 0.9)
        out.append(Anomaly(label=label, confidence=round(conf, 2),
                            area_ratio=round(ratio, 4), bbox=(x, y, w, h)))
    return out


def analyze_defects(crop_bgr: np.ndarray):
    """Top-level entry point used by the pipeline orchestrator.

    Returns (anomalies, produce_mask, total_defect_coverage_ratio).
    """
    produce_mask = segment_produce_mask(crop_bgr)
    anomalies = find_anomalies(crop_bgr, produce_mask)

    # Refine generic labels using local color stats for richer explanations
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    refined: List[Anomaly] = []
    for a in anomalies:
        x, y, w, h = a.bbox
        patch = hsv[y:y + h, x:x + w]
        label, _ = _refine_label(a.label, patch) if a.label != "crack_or_cut" else (a.label, a.confidence)
        refined.append(Anomaly(label=label, confidence=a.confidence, area_ratio=a.area_ratio, bbox=a.bbox))

    total_coverage = min(sum(a.area_ratio for a in refined), 1.0)
    return refined, produce_mask, total_coverage
