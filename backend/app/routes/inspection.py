"""Inspection routes — hardened, storage-adapter-aware."""
import logging
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response

from app.core.auth import get_current_user
from app.core.config import MAX_UPLOAD_BYTES, OVERLAY_DIR
from app.core.security import validate_image_bytes
from app.db.database import save_inspection, get_inspections, get_inspection_detail, log_audit
from app.services.pipeline import run_inspection
from app.services.storage import save_image, save_overlay, get_overlay_bytes, using_supabase

logger = logging.getLogger("freshvision.routes.inspection")
router = APIRouter(prefix="/api/inspect", tags=["inspection"])


def _decode(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Could not decode image — file may be corrupt.")
    return img


async def _run_one(contents, warehouse_id, supplier_id, temp, humid, username, rid=""):
    validate_image_bytes(contents)
    image = _decode(contents)
    result, overlay = run_inspection(image, storage_temp_c=temp, storage_humidity_pct=humid)
    iid = result["inspection_id"]

    img_path = await save_image(iid, image)
    ov_path  = await save_overlay(iid, overlay)

    result["warehouse_id"] = warehouse_id
    result["supplier_id"]  = supplier_id
    await save_inspection(result, img_path, ov_path, warehouse_id, supplier_id,
                           owner_username=username)
    await log_audit(username, "inspect", f"iid={iid} items={len(result['items'])} rid={rid}")

    # If using Supabase storage, ov_path is already a public URL
    result["overlay_url"] = ov_path if using_supabase() else f"/api/inspect/overlay/{iid}"
    result["timestamp"]   = result["timestamp"].isoformat()
    return result


@router.post("")
async def inspect_image(
    request:              Request,
    file:                 UploadFile       = File(...),
    warehouse_id:         Optional[str]   = Form("WH-DEFAULT"),
    supplier_id:          Optional[str]   = Form(None),
    storage_temp_c:       Optional[float] = Form(6.0),
    storage_humidity_pct: Optional[float] = Form(85.0),
    current_user=Depends(get_current_user),
):
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File too large (max {MAX_UPLOAD_BYTES//1_048_576} MB)")
    try:
        validate_image_bytes(contents)
    except ValueError as exc:
        raise HTTPException(415, str(exc))

    temp  = max(-30.0, min(60.0,  storage_temp_c       or 6.0))
    humid = max(0.0,   min(100.0, storage_humidity_pct or 85.0))
    rid   = getattr(request.state, "request_id", "?")
    return await _run_one(contents, warehouse_id, supplier_id, temp, humid,
                          current_user["username"], rid)


@router.post("/batch")
async def inspect_batch(
    files:                list[UploadFile] = File(...),
    warehouse_id:         Optional[str]   = Form("WH-DEFAULT"),
    supplier_id:          Optional[str]   = Form(None),
    storage_temp_c:       Optional[float] = Form(6.0),
    storage_humidity_pct: Optional[float] = Form(85.0),
    current_user=Depends(get_current_user),
):
    if len(files) > 8:
        raise HTTPException(400, "Batch limit is 8 images per request.")
    temp  = max(-30.0, min(60.0,  storage_temp_c       or 6.0))
    humid = max(0.0,   min(100.0, storage_humidity_pct or 85.0))
    results = []
    for f in files:
        contents = await f.read(MAX_UPLOAD_BYTES + 1)
        if len(contents) > MAX_UPLOAD_BYTES:
            results.append({"filename": f.filename, "error": "File too large"}); continue
        try:
            r = await _run_one(contents, warehouse_id, supplier_id, temp, humid,
                               current_user["username"])
            r["filename"] = f.filename
            results.append(r)
        except Exception as exc:
            results.append({"filename": f.filename, "error": str(exc)})
    return {"batch_results": results, "total": len(results)}


def _owner_filter(current_user) -> Optional[str]:
    """Admins can see every user's data; everyone else only sees their own."""
    return None if current_user["role"] == "admin" else current_user["username"]


@router.get("/history")
async def history(limit=50, offset=0, warehouse_id=None, supplier_id=None,
                  current_user=Depends(get_current_user)):
    return await get_inspections(limit=min(limit,200), offset=offset,
                                  warehouse_id=warehouse_id, supplier_id=supplier_id,
                                  owner_username=_owner_filter(current_user))


@router.get("/{inspection_id}")
async def inspection_detail(inspection_id: str, current_user=Depends(get_current_user)):
    if not inspection_id.isalnum() or len(inspection_id) > 32:
        raise HTTPException(400, "Invalid inspection ID")
    row = await get_inspection_detail(inspection_id, owner_username=_owner_filter(current_user))
    if not row:
        raise HTTPException(404, "Inspection not found")
    return row


@router.get("/overlay/{inspection_id}")
async def get_overlay(inspection_id: str, current_user=Depends(get_current_user)):
    """Serves overlay from local disk (Supabase mode returns public URL instead)."""
    if not inspection_id.isalnum() or len(inspection_id) > 32:
        raise HTTPException(400, "Invalid inspection ID")
    # Ownership check first so we never leak another user's overlay image.
    owned = await get_inspection_detail(inspection_id, owner_username=_owner_filter(current_user))
    if not owned:
        raise HTTPException(404, "Overlay not found")
    data = await get_overlay_bytes(inspection_id)
    if not data:
        raise HTTPException(404, "Overlay not found")
    return Response(content=data, media_type="image/jpeg",
                    headers={"Cache-Control": "private, max-age=86400"})
