"""
Explainability — draws bounding boxes, defect masks, and grade/decision
labels directly on the image so an inspector can see *why* a call was made,
without needing to read a report.
"""
from typing import List
import cv2
import numpy as np

GRADE_COLORS = {
    "Premium": (80, 220, 130),
    "Grade A": (90, 200, 90),
    "Grade B": (40, 190, 230),
    "Grade C": (30, 150, 235),
    "Reject": (50, 60, 230),
}
DEFECT_COLOR = (40, 40, 235)


def draw_overlay(image_bgr: np.ndarray, items: list) -> np.ndarray:
    """`items` is a list of dicts each with bbox, product_type, quality_grade,
    decision, and defects (list of dicts with bbox-in-crop + label)."""
    canvas = image_bgr.copy()

    for item in items:
        x, y, w, h = item["bbox"]
        color = GRADE_COLORS.get(item["quality_grade"], (200, 200, 200))
        cv2.rectangle(canvas, (x, y), (x + w, y + h), color, 2)

        label = f"{item['product_type']} | {item['quality_grade']} | {item['decision']}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        cv2.rectangle(canvas, (x, max(0, y - th - 10)), (x + tw + 8, y), color, -1)
        cv2.putText(canvas, label, (x + 4, max(12, y - 6)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (15, 15, 15), 2, cv2.LINE_AA)

        for d in item["defects"]:
            dx, dy, dw, dh = d["bbox"]
            cv2.rectangle(canvas, (x + dx, y + dy), (x + dx + dw, y + dy + dh), DEFECT_COLOR, 1)
            cv2.putText(canvas, d["label"], (x + dx, max(10, y + dy - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, DEFECT_COLOR, 1, cv2.LINE_AA)

    return canvas
