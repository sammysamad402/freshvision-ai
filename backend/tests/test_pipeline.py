"""
FreshVision AI — Test Suite
Run: cd backend && python -m pytest tests/ -v --tb=short
"""
import sys
import pytest
import numpy as np
import cv2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Fixtures ─────────────────────────────────────────────────────────────────

def make_image(bgr=(40, 40, 200), size=280, bruise=False, mold=False, dark=False):
    """Create a synthetic produce image for testing."""
    img = np.full((size, size, 3), 245, dtype=np.uint8)
    cx, cy, r = size // 2, size // 2, size // 2 - 20
    cv2.circle(img, (cx, cy), r, bgr, -1)
    if bruise:
        cv2.circle(img, (cx + 35, cy - 25), 20, (30, 60, 90), -1)
    if mold:
        cv2.circle(img, (cx - 30, cy + 30), 16, (200, 200, 200), -1)
    if dark:
        cv2.circle(img, (cx + 10, cy + 40), 9, (12, 12, 12), -1)
    return img


@pytest.fixture
def clean_apple():
    return make_image(bgr=(40, 40, 200))


@pytest.fixture
def bruised_apple():
    return make_image(bgr=(40, 40, 200), bruise=True)


@pytest.fixture
def moldy_orange():
    return make_image(bgr=(30, 110, 235), mold=True, dark=True)


# ── Security tests ────────────────────────────────────────────────────────────

class TestMagicByteValidation:
    def test_valid_jpeg(self):
        from app.core.security import validate_image_bytes
        jpeg_magic = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        assert validate_image_bytes(jpeg_magic) == "image/jpeg"

    def test_valid_png(self):
        from app.core.security import validate_image_bytes
        png_magic = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert validate_image_bytes(png_magic) == "image/png"

    def test_rejects_php_disguised_as_jpg(self):
        from app.core.security import validate_image_bytes
        php_bytes = b"<?php echo 'evil'; ?>" + b"\x00" * 100
        with pytest.raises(ValueError, match="Unsupported file type"):
            validate_image_bytes(php_bytes)

    def test_rejects_pdf_disguised_as_png(self):
        from app.core.security import validate_image_bytes
        pdf_bytes = b"%PDF-1.4" + b"\x00" * 100
        with pytest.raises(ValueError):
            validate_image_bytes(pdf_bytes)

    def test_rejects_empty(self):
        from app.core.security import validate_image_bytes
        with pytest.raises(ValueError):
            validate_image_bytes(b"")


# ── Defect analysis tests ─────────────────────────────────────────────────────

class TestDefectAnalysis:
    def test_clean_produce_low_coverage(self, clean_apple):
        from app.services.defect_analysis import analyze_defects
        anomalies, mask, coverage = analyze_defects(clean_apple)
        assert coverage < 0.10, f"Clean apple should have <10% coverage, got {coverage:.2%}"

    def test_bruise_detected(self, bruised_apple):
        from app.services.defect_analysis import analyze_defects
        anomalies, mask, coverage = analyze_defects(bruised_apple)
        labels = [a.label for a in anomalies]
        assert any("bruise" in l or "dark" in l or "spot" in l for l in labels), \
            f"Expected bruise/dark defect, got: {labels}"

    def test_mold_detected(self, moldy_orange):
        from app.services.defect_analysis import analyze_defects
        anomalies, mask, coverage = analyze_defects(moldy_orange)
        assert len(anomalies) > 0, "Moldy orange should have at least one anomaly"
        assert coverage > 0.005, f"Expected some defect coverage, got {coverage:.4f}"

    def test_mask_nonzero(self, clean_apple):
        from app.services.defect_analysis import analyze_defects
        _, mask, _ = analyze_defects(clean_apple)
        assert np.count_nonzero(mask) > 0, "Produce mask should be non-empty"

    def test_anomaly_bbox_within_image(self, bruised_apple):
        from app.services.defect_analysis import analyze_defects
        anomalies, _, _ = analyze_defects(bruised_apple)
        h, w = bruised_apple.shape[:2]
        for a in anomalies:
            x, y, aw, ah = a.bbox
            assert x >= 0 and y >= 0
            assert x + aw <= w and y + ah <= h, f"BBox {a.bbox} out of bounds for {w}×{h}"

    def test_confidence_range(self, bruised_apple):
        from app.services.defect_analysis import analyze_defects
        anomalies, _, _ = analyze_defects(bruised_apple)
        for a in anomalies:
            assert 0.0 <= a.confidence <= 1.0, f"Confidence {a.confidence} out of [0,1]"


# ── Quality grading tests ─────────────────────────────────────────────────────

class TestGrading:
    def test_no_defects_premium(self):
        from app.services.grading import grade_product
        grade, score, _ = grade_product([], 0.0)
        assert grade == "Premium"
        assert score > 90

    def test_heavy_defects_reject(self):
        from app.services.defect_analysis import Anomaly
        from app.services.grading import grade_product
        bad = [Anomaly(label="mold_fungus", confidence=0.9, area_ratio=0.15, bbox=(0,0,10,10)),
               Anomaly(label="black_spot",  confidence=0.85, area_ratio=0.12, bbox=(20,20,8,8))]
        grade, score, _ = grade_product(bad, 0.27)
        assert grade == "Reject"
        assert score < 50

    def test_mild_defect_grade_a_or_b(self):
        from app.services.defect_analysis import Anomaly
        from app.services.grading import grade_product
        mild = [Anomaly(label="discoloration", confidence=0.6, area_ratio=0.025, bbox=(0,0,5,5))]
        grade, score, _ = grade_product(mild, 0.025)
        assert grade in ("Grade A", "Grade B")

    def test_explanation_populated(self, bruised_apple):
        from app.services.defect_analysis import analyze_defects
        from app.services.grading import grade_product
        anomalies, _, coverage = analyze_defects(bruised_apple)
        _, _, explanation = grade_product(anomalies, coverage)
        assert len(explanation) > 10

    def test_quality_score_bounded(self):
        from app.services.defect_analysis import Anomaly
        from app.services.grading import grade_product
        for coverage in [0.0, 0.05, 0.15, 0.50, 1.0]:
            _, score, _ = grade_product([], coverage)
            assert 0.0 <= score <= 100.0, f"Score {score} out of range at coverage={coverage}"


# ── Freshness prediction tests ────────────────────────────────────────────────

class TestFreshness:
    def test_fresh_vibrant_produce(self, clean_apple):
        from app.services.defect_analysis import segment_produce_mask
        from app.services.freshness import predict_freshness
        mask = segment_produce_mask(clean_apple)
        label, pct, conf = predict_freshness(clean_apple, mask, 0.0)
        assert pct > 40, f"Expected decent freshness for clean apple, got {pct}"
        assert label in ("Fresh", "Good", "Needs Quick Sale")

    def test_spoiled_low_freshness(self):
        """Orange with heavy defects AND low saturation should score below 85."""
        from app.services.defect_analysis import analyze_defects, segment_produce_mask
        from app.services.freshness import predict_freshness
        import numpy as np, cv2
        # Build a dull, heavily damaged fruit
        img = np.full((280, 280, 3), 245, dtype=np.uint8)
        cv2.circle(img, (140, 140), 100, (90, 90, 90), -1)   # grey/washed-out body
        cv2.circle(img, (100, 120), 30, (20, 20, 20), -1)    # large dark rot
        cv2.circle(img, (170, 170), 25, (200, 200, 200), -1) # mold patch
        _, mask, coverage = analyze_defects(img)
        _, pct, _ = predict_freshness(img, mask, coverage)
        assert pct < 85, f"Heavily damaged, low-saturation produce should not score ≥85, got {pct}"

    def test_confidence_range(self, clean_apple):
        from app.services.defect_analysis import segment_produce_mask
        from app.services.freshness import predict_freshness
        mask = segment_produce_mask(clean_apple)
        _, _, conf = predict_freshness(clean_apple, mask, 0.0)
        assert 0.0 <= conf <= 1.0

    def test_shelf_life_decreases_with_temp(self):
        from app.services.freshness import predict_shelf_life
        days_cold, _, _ = predict_shelf_life(80.0, storage_temp_c=4.0)
        days_warm, _, _ = predict_shelf_life(80.0, storage_temp_c=20.0)
        assert days_cold > days_warm, "Cold storage should give more shelf life"

    def test_shelf_life_nonnegative(self):
        from app.services.freshness import predict_shelf_life
        for fp in [0, 10, 50, 100]:
            days, _, _ = predict_shelf_life(fp, storage_temp_c=30.0)
            assert days >= 0.0, f"Shelf life negative at freshness={fp}"


# ── Decision engine tests ─────────────────────────────────────────────────────

class TestDecisionEngine:
    def test_premium_accepted(self):
        from app.services.decision_engine import decide
        decision, reasons = decide("apple", "Premium", "Fresh", 8.0, 0.0)
        assert decision == "Accept"

    def test_spoiled_rejected(self):
        from app.services.decision_engine import decide
        decision, _ = decide("apple", "Reject", "Spoiled", 0.0, 0.5)
        assert decision == "Reject"

    def test_near_expiry_priority_dispatch(self):
        from app.services.decision_engine import decide
        decision, _ = decide("banana", "Grade B", "Near Expiry", 0.5, 0.05)
        assert decision in ("Priority Dispatch", "Reject")

    def test_egg_cold_storage(self):
        from app.services.decision_engine import decide
        decision, _ = decide("egg", "Premium", "Fresh", 10.0, 0.0)
        assert decision == "Cold Storage Required"

    def test_high_defect_manual_inspection(self):
        from app.services.decision_engine import decide
        decision, _ = decide("orange", "Grade C", "Good", 4.0, 0.18)
        assert decision in ("Manual Inspection", "Reject")

    def test_reasons_populated(self):
        from app.services.decision_engine import decide
        _, reasons = decide("apple", "Premium", "Fresh", 8.0, 0.0)
        assert len(reasons) > 0
        assert all(isinstance(r, str) for r in reasons)


# ── Full pipeline integration test ────────────────────────────────────────────

class TestPipeline:
    def test_end_to_end_returns_expected_keys(self, clean_apple):
        from app.services.pipeline import run_inspection
        result, overlay = run_inspection(clean_apple, storage_temp_c=6.0, storage_humidity_pct=85.0)
        assert "inspection_id" in result
        assert "items" in result
        assert len(result["items"]) > 0
        item = result["items"][0]
        for key in ("product_type", "quality_grade", "freshness_label",
                    "shelf_life_days", "decision", "explanation"):
            assert key in item, f"Missing key: {key}"

    def test_overlay_shape_matches_input(self, clean_apple):
        from app.services.pipeline import run_inspection
        _, overlay = run_inspection(clean_apple)
        assert overlay.shape == clean_apple.shape, "Overlay shape must match input"

    def test_deterministic_output(self, clean_apple):
        """Same image → same grade (pipeline is stateless)."""
        from app.services.pipeline import run_inspection
        r1, _ = run_inspection(clean_apple)
        r2, _ = run_inspection(clean_apple)
        assert r1["items"][0]["quality_grade"] == r2["items"][0]["quality_grade"]

    def test_temp_affects_shelf_life(self, clean_apple):
        from app.services.pipeline import run_inspection
        r_cold, _ = run_inspection(clean_apple, storage_temp_c=4.0,  storage_humidity_pct=85.0)
        r_warm, _ = run_inspection(clean_apple, storage_temp_c=22.0, storage_humidity_pct=85.0)
        cold_days = r_cold["items"][0]["shelf_life_days"]
        warm_days = r_warm["items"][0]["shelf_life_days"]
        assert cold_days >= warm_days, "Cold storage must give ≥ shelf life vs warm"

    def test_unique_inspection_ids(self, clean_apple):
        from app.services.pipeline import run_inspection
        ids = {run_inspection(clean_apple)[0]["inspection_id"] for _ in range(5)}
        assert len(ids) == 5, "Each inspection must have a unique ID"
