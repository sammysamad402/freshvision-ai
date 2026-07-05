"""Decision engine -- final accept/reject/dispatch logic, always with reasons."""
from typing import List, Tuple
from app.core.config import COLD_CHAIN_PRODUCTS


def decide(
    product_type: str,
    grade: str,
    freshness_label: str,
    shelf_life_days: float,
    defect_coverage_pct: float,
) -> Tuple[str, List[str]]:
    reasons: List[str] = []

    if grade == "Reject" or freshness_label == "Spoiled":
        decision = "Reject"
        reasons.append(f"Grade={grade}, Freshness={freshness_label} -- below acceptable threshold")
        return decision, reasons

    if defect_coverage_pct > 0.15 and grade in ("Grade B", "Grade C"):
        reasons.append(f"Defect coverage {defect_coverage_pct*100:.1f}% -- borderline, needs human eyes")
        return "Manual Inspection", reasons

    if shelf_life_days <= 1.0 or freshness_label == "Near Expiry":
        reasons.append(f"Only {shelf_life_days} day(s) of shelf life remaining")
        return "Priority Dispatch", reasons

    if freshness_label == "Needs Quick Sale":
        reasons.append("Freshness declining -- recommend immediate sale window")
        return "Immediate Sale", reasons

    if product_type in COLD_CHAIN_PRODUCTS:
        reasons.append(f"{product_type} requires continuous cold-chain storage")
        return "Cold Storage Required", reasons

    reasons.append(f"Grade={grade}, Freshness={freshness_label}, Shelf life={shelf_life_days}d -- within spec")
    return "Accept", reasons
