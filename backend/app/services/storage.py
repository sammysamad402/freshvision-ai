"""
FreshVision AI — Storage adapter.

Transparently supports two backends:
  • Local disk  (default, local dev + Docker)
  • Supabase Storage (production — set SUPABASE_URL + SUPABASE_KEY in .env)

When Supabase is configured:
  - Images are uploaded to the `freshvision` bucket
  - Overlay URLs are public (no auth needed to view annotated images)
  - Original uploads are private (only the API can access them)
"""
import logging
import os
from pathlib import Path

import cv2
import numpy as np

from app.core.config import UPLOAD_DIR, OVERLAY_DIR

logger = logging.getLogger("freshvision.storage")

_supabase_client = None
_BUCKET = "freshvision"


def _get_supabase():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
        # Ensure bucket exists (ignore error if already exists)
        try:
            _supabase_client.storage.create_bucket(
                _BUCKET, options={"public": False}
            )
        except Exception:
            pass
        logger.info("Supabase Storage initialised  bucket=%s", _BUCKET)
    except Exception as exc:
        logger.warning("Supabase Storage unavailable: %s — using local disk", exc)
        _supabase_client = None
    return _supabase_client


def _encode_jpg(image_bgr: np.ndarray, quality: int = 88) -> bytes:
    ok, buf = cv2.imencode(".jpg", image_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("Failed to encode image as JPEG")
    return bytes(buf)


async def save_image(inspection_id: str, image_bgr: np.ndarray) -> str:
    """
    Save the original uploaded image.
    Returns: path (local) or Supabase storage path.
    """
    sb = _get_supabase()
    filename = f"uploads/{inspection_id}_src.jpg"
    data = _encode_jpg(image_bgr, quality=90)

    if sb:
        try:
            sb.storage.from_(_BUCKET).upload(
                filename, data, {"content-type": "image/jpeg", "upsert": "true"}
            )
            return filename          # Supabase path
        except Exception as exc:
            logger.error("Supabase upload failed: %s — falling back to local", exc)

    # Local fallback
    local_path = UPLOAD_DIR / f"{inspection_id}_src.jpg"
    local_path.write_bytes(data)
    return str(local_path)


async def save_overlay(inspection_id: str, overlay_bgr: np.ndarray) -> str:
    """
    Save the annotated overlay image.
    Returns: public URL (Supabase) or local path (disk).
    """
    sb = _get_supabase()
    filename = f"overlays/{inspection_id}_overlay.jpg"
    data = _encode_jpg(overlay_bgr, quality=88)

    if sb:
        try:
            # Upload to a public path so the frontend can load it without auth
            sb.storage.from_(_BUCKET).upload(
                filename, data, {"content-type": "image/jpeg", "upsert": "true"}
            )
            public_url = sb.storage.from_(_BUCKET).get_public_url(filename)
            return public_url
        except Exception as exc:
            logger.error("Supabase overlay upload failed: %s — falling back to local", exc)

    # Local fallback
    local_path = OVERLAY_DIR / f"{inspection_id}_overlay.jpg"
    local_path.write_bytes(data)
    return str(local_path)


async def get_overlay_bytes(inspection_id: str) -> bytes:
    """Return overlay image bytes — used by the local-disk overlay endpoint."""
    local_path = OVERLAY_DIR / f"{inspection_id}_overlay.jpg"
    if local_path.exists():
        return local_path.read_bytes()
    return b""


def using_supabase() -> bool:
    return _get_supabase() is not None
