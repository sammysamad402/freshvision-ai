"""
Demo data seeder.

Populates the database with 30 days of realistic inspection history across
multiple warehouses and suppliers so the analytics dashboard is fully
populated the moment judges see it.

Usage:
    cd backend
    python -m scripts.seed_demo_data          # 30 days
    python -m scripts.seed_demo_data --days 7  # quick seed
    python -m scripts.seed_demo_data --clear   # wipe and reseed
"""
import argparse
import asyncio
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import DB_PATH
from app.db.database import init_db, save_inspection
from app.services.pipeline import run_inspection

# ── Produce profiles ──────────────────────────────────────────────────────
# Each profile defines what to draw and how "damaged" to make it,
# so we get realistic grade/freshness distributions not just all-perfect.

PRODUCE_PROFILES = [
    # (name, body_bgr, defect_prob, severe_prob)
    ("apple",       (40,  40, 200), 0.30, 0.10),
    ("banana",      (30, 200, 230), 0.25, 0.08),
    ("orange",      (30, 130, 235), 0.35, 0.12),
    ("broccoli",    (60, 160,  60), 0.20, 0.06),
    ("carrot",      (40, 130, 220), 0.22, 0.07),
    ("tomato",      (35,  55, 210), 0.28, 0.09),
    ("lettuce",     (60, 180,  80), 0.18, 0.05),
    ("strawberry",  (50,  60, 200), 0.40, 0.15),
]

WAREHOUSES  = ["WH-001", "WH-002", "WH-003", "WH-004"]
SUPPLIERS   = ["SUP-FARM-A", "SUP-FARM-B", "SUP-ORGANIC-C"]

# Supplier quality biases (0 = perfect, 1 = terrible)
SUPPLIER_QUALITY = {"SUP-FARM-A": 0.15, "SUP-FARM-B": 0.28, "SUP-ORGANIC-C": 0.08}

INSPECTIONS_PER_DAY_RANGE = (8, 20)
ITEMS_PER_INSPECTION_RANGE = (1, 4)


def _make_produce_image(profile_name: str, body_bgr: tuple,
                         defect_prob: float, severe_prob: float,
                         supplier_bias: float) -> np.ndarray:
    """Draw a synthetic produce image on a white-ish inspection tray."""
    w, h = 320, 320
    img = np.full((h, w, 3), random.randint(235, 250), dtype=np.uint8)

    # Slightly vary the body colour to simulate natural variation
    b, g, r = body_bgr
    jitter = 20
    body = (
        max(0, min(255, b + random.randint(-jitter, jitter))),
        max(0, min(255, g + random.randint(-jitter, jitter))),
        max(0, min(255, r + random.randint(-jitter, jitter))),
    )

    cx, cy = w // 2 + random.randint(-20, 20), h // 2 + random.randint(-20, 20)
    radius = random.randint(80, 100)
    cv2.ellipse(img, (cx, cy), (radius, int(radius * random.uniform(0.85, 1.0))),
                random.randint(0, 30), 0, 360, body, -1)

    effective_defect = min(defect_prob + supplier_bias * 0.4, 0.85)
    effective_severe = min(severe_prob + supplier_bias * 0.2, 0.50)

    if random.random() < effective_defect:
        n_defects = random.randint(1, 3)
        for _ in range(n_defects):
            dx = cx + random.randint(-radius + 15, radius - 15)
            dy = cy + random.randint(-radius + 15, radius - 15)
            dr = random.randint(8, 22)
            defect_type = random.choices(
                ["bruise", "mold", "dark_spot", "discolor"],
                weights=[0.40, 0.20, 0.25, 0.15]
            )[0]
            if defect_type == "bruise":
                dc = (max(0, b - 60), max(0, g - 50), max(0, r - 80))
            elif defect_type == "mold":
                dc = (200, 200, 200)
            elif defect_type == "dark_spot":
                dc = (15, 15, 15)
            else:
                dc = (max(0, b - 30), min(255, g + 40), max(0, r - 20))
            cv2.circle(img, (dx, dy), dr, dc, -1)

    if random.random() < effective_severe:
        # Add a large spoilage patch
        sx = cx + random.randint(-30, 30)
        sy = cy + random.randint(-30, 30)
        cv2.ellipse(img, (sx, sy), (random.randint(20, 35), random.randint(15, 28)),
                    random.randint(0, 180), 0, 360,
                    (20, 20, 20) if random.random() < 0.5 else (180, 180, 180), -1)

    return img


async def seed(days: int = 30, clear: bool = False):
    if clear and DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Cleared database: {DB_PATH}")

    await init_db()
    print(f"Seeding {days} days of demo data…")

    now = datetime.now(timezone.utc)
    total_inspections = 0
    total_items = 0

    for day_offset in range(days, 0, -1):
        day_dt = now - timedelta(days=day_offset)
        n_inspections = random.randint(*INSPECTIONS_PER_DAY_RANGE)

        for _ in range(n_inspections):
            warehouse = random.choice(WAREHOUSES)
            supplier  = random.choice(SUPPLIERS)
            bias      = SUPPLIER_QUALITY[supplier]
            temp      = round(random.uniform(3.0, 16.0), 1)
            humid     = round(random.uniform(65.0, 95.0), 1)

            # Randomise timestamp within business hours
            ts_hour   = random.randint(6, 20)
            ts_min    = random.randint(0, 59)
            insp_ts   = day_dt.replace(hour=ts_hour, minute=ts_min, second=0, microsecond=0)

            n_items = random.randint(*ITEMS_PER_INSPECTION_RANGE)
            stacked_images = []
            for _ in range(n_items):
                name, body_bgr, dp, sp = random.choice(PRODUCE_PROFILES)
                img = _make_produce_image(name, body_bgr, dp, sp, bias)
                stacked_images.append(img)

            # Concatenate items side-by-side in one image (simulates belt scan)
            frame = np.concatenate(stacked_images, axis=1)

            result, overlay = run_inspection(frame, storage_temp_c=temp, storage_humidity_pct=humid)

            # Back-date the timestamp so analytics trend charts have real dates
            result["timestamp"] = insp_ts
            result["warehouse_id"] = warehouse
            result["supplier_id"]  = supplier

            await save_inspection(
                result,
                f"/data/demo/{result['inspection_id']}_src.jpg",
                f"/data/demo/{result['inspection_id']}_ov.jpg",
                warehouse, supplier,
            )
            total_inspections += 1
            total_items += len(result["items"])

        print(f"  Day -{day_offset:2d}: {n_inspections} inspections seeded")

    print(f"\nDone. {total_inspections} inspections / {total_items} items seeded.")
    print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed FreshVision demo data")
    parser.add_argument("--days",  type=int, default=30,   help="Days of history to generate")
    parser.add_argument("--clear", action="store_true",    help="Wipe DB before seeding")
    args = parser.parse_args()
    asyncio.run(seed(days=args.days, clear=args.clear))
