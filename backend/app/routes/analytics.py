"""Analytics and report export routes."""
import io
import csv
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.auth import get_current_user
from app.db.database import get_analytics, get_inspections

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _owner_filter(current_user) -> Optional[str]:
    """Admins can see every user's data; everyone else only sees their own."""
    return None if current_user["role"] == "admin" else current_user["username"]


@router.get("/summary")
async def summary(
    days: int = Query(30, ge=1, le=365),
    warehouse_id: Optional[str] = None,
    supplier_id: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    return await get_analytics(days=days, warehouse_id=warehouse_id, supplier_id=supplier_id,
                                owner_username=_owner_filter(current_user))


@router.get("/export/csv")
async def export_csv(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
):
    """Stream inspection history as a CSV download (only the caller's own data)."""
    rows = await get_inspections(limit=10000, owner_username=_owner_filter(current_user))

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "inspection_id", "timestamp", "warehouse_id", "supplier_id",
        "storage_temp_c", "storage_humidity_pct", "item_count",
    ])
    for r in rows:
        writer.writerow([
            r.get("inspection_id"), r.get("timestamp"), r.get("warehouse_id"),
            r.get("supplier_id"), r.get("storage_temp_c"), r.get("storage_humidity_pct"),
            r.get("item_count"),
        ])
    buf.seek(0)

    filename = f"freshvision_export_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
