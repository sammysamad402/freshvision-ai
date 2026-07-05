"""Quality grading -- maps defect coverage + defect severity to a grade."""
from typing import List
from app.core.config import GRADE_THRESHOLDS
from app.services.defect_analysis import Anomaly

SEVERITY_WEIGHT = {
    "black_spot": 1.4,
    "mold_fungus": 1.6,
    "bruise_or_rot": 1.2,
    "crack_or_cut": 1.1,
    "discoloration": 0.8,
}


def grade_product(anomalies: List[Anomaly], defect_coverage_pct: float):
    """
    Returns (grade, quality_score_0_100, explanation_str).

    Coverage is weighted by defect severity (mold/black spots count more
    per-pixel than mild discoloration) before being compared against the
    grade thresholds, so two products with identical raw coverage but
    different defect types can land in different grades.
    """
    if not anomalies:
        weighted_coverage = 0.0
    else:
        weighted_sum = sum(a.area_ratio * SEVERITY_WEIGHT.get(a.label, 1.0) for a in anomalies)
        weighted_coverage = weighted_sum

    grade = "Reject"
    for label, ceiling in GRADE_THRESHOLDS.items():
        if weighted_coverage < ceiling:
            grade = label
            break

    quality_score = max(0.0, round(100 * (1 - min(weighted_coverage * 2.2, 1.0)), 1))

    if not anomalies:
        explanation = "No visible defects detected; surface is uniform and unblemished."
    else:
        top = sorted(anomalies, key=lambda a: a.area_ratio, reverse=True)[:3]
        parts = [f"{a.label.replace('_', ' ')} ({a.area_ratio*100:.1f}% of surface)" for a in top]
        explanation = (
            f"Detected {len(anomalies)} defect region(s): " + ", ".join(parts) +
            f". Weighted defect coverage: {weighted_coverage*100:.1f}%."
        )

    return grade, quality_score, explanation
