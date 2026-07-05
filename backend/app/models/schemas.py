"""Pydantic models shared across the API."""
import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class DefectFinding(BaseModel):
    label: str
    confidence: float
    area_ratio: float          # fraction of produce surface covered
    bbox: List[int]            # [x, y, w, h] in the cropped product frame


class DetectedItem(BaseModel):
    item_id: str
    product_type: str
    detection_confidence: float
    bbox: List[int]            # [x, y, w, h] in the original image
    defects: List[DefectFinding]
    defect_coverage_pct: float
    quality_grade: str
    quality_score: float
    freshness_label: str
    freshness_pct: float
    shelf_life_days: float
    shelf_life_confidence: float
    decision: str
    decision_reasons: List[str]
    explanation: str


class InspectionResult(BaseModel):
    inspection_id: str
    timestamp: datetime
    warehouse_id: Optional[str] = "WH-DEFAULT"
    supplier_id: Optional[str] = None
    image_path: str
    overlay_path: str
    items: List[DetectedItem]
    storage_temp_c: Optional[float] = None
    storage_humidity_pct: Optional[float] = None


class AnalyticsSummary(BaseModel):
    total_inspections: int
    total_items: int
    grade_distribution: dict
    freshness_distribution: dict
    decision_distribution: dict
    avg_defect_coverage_pct: float
    rejected_count: int
    by_supplier: dict
    by_warehouse: dict
    recent_trend: list


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    username: str
    role: str


_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def username_format(cls, v: str) -> str:
        v = v.strip()
        if not _USERNAME_RE.match(v):
            raise ValueError(
                "Username must be 3-32 characters: letters, numbers, dot, dash, underscore only."
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        has_letter = re.search(r"[A-Za-z]", v)
        has_digit  = re.search(r"\d", v)
        if not (has_letter and has_digit):
            raise ValueError("Password must contain at least one letter and one number.")
        return v
