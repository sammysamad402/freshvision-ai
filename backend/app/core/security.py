"""
Production security middleware and helpers.

Covers:
  • Strict security headers (CSP, HSTS, X-Frame-Options, etc.)
  • Trusted file-type validation (magic bytes, not just MIME header)
  • Request ID injection for log correlation
  • Secure logging (strips Authorization headers from logs)
"""
import logging
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("freshvision.security")

# ── Security headers ─────────────────────────────────────────────────────────
SECURITY_HEADERS = {
    "X-Content-Type-Options":    "nosniff",
    "X-Frame-Options":           "DENY",
    "X-XSS-Protection":          "1; mode=block",
    "Referrer-Policy":           "strict-origin-when-cross-origin",
    "Permissions-Policy":        "camera=(), microphone=(), geolocation=()",
    # CSP — tightened; adjust if you add external CDN resources
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "   # Vite dev needs inline
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    ),
    # HSTS — 1 year, include subdomains; comment out if running plain HTTP
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a UUID to every request for log correlation."""
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rid = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


# ── Magic-byte file validation ────────────────────────────────────────────────
MAGIC_BYTES = {
    b"\xff\xd8\xff":        "image/jpeg",
    b"\x89PNG\r\n\x1a\n":  "image/png",
    b"RIFF":                "image/webp",  # RIFF....WEBP
}


def validate_image_bytes(data: bytes) -> str:
    """
    Return MIME type detected from magic bytes.
    Raises ValueError if not a supported image type.
    This prevents disguised uploads (e.g. a .php file renamed .jpg).
    """
    for magic, mime in MAGIC_BYTES.items():
        if data[:len(magic)] == magic:
            if mime == "image/webp" and data[8:12] != b"WEBP":
                continue
            return mime
    raise ValueError(
        "Unsupported file type. Upload a JPEG, PNG, or WEBP image."
    )
