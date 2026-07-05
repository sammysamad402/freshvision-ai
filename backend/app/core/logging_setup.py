"""
Structured logging with daily rotation and sensitive-field redaction.

Log levels:
  DEBUG   — detailed pipeline timing (set LOG_LEVEL=DEBUG in dev)
  INFO    — normal operations (default)
  WARNING — recoverable issues (YOLO fallback, etc.)
  ERROR   — unhandled exceptions

Files:
  storage/logs/freshvision.log           — all levels (rotated daily, 14 days)
  storage/logs/freshvision_errors.log    — ERROR+ only
"""
import logging
import logging.handlers
import re
import sys
from pathlib import Path

from app.core.config import LOG_DIR

_REDACT_PATTERN = re.compile(
    r'(Authorization|password|token|secret)["\']?\s*[:=]\s*["\']?[\w\-\.]+',
    re.IGNORECASE,
)


class _RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.getMessage():
            record.msg = _REDACT_PATTERN.sub(r"\1=***REDACTED***", str(record.msg))
        return True


def setup_logging(log_level: str = "INFO") -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt)
    console.addFilter(_RedactFilter())
    root.addHandler(console)

    # Rotating file handler — all levels
    all_log = LOG_DIR / "freshvision.log"
    file_h = logging.handlers.TimedRotatingFileHandler(
        all_log, when="midnight", backupCount=14, encoding="utf-8"
    )
    file_h.setLevel(level)
    file_h.setFormatter(fmt)
    file_h.addFilter(_RedactFilter())
    root.addHandler(file_h)

    # Error-only file handler
    err_log = LOG_DIR / "freshvision_errors.log"
    err_h = logging.handlers.TimedRotatingFileHandler(
        err_log, when="midnight", backupCount=30, encoding="utf-8"
    )
    err_h.setLevel(logging.ERROR)
    err_h.setFormatter(fmt)
    root.addHandler(err_h)

    # Silence noisy third-party loggers
    for noisy in ("ultralytics", "PIL", "httpx", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("freshvision").info(
        "Logging initialised  level=%s  file=%s", log_level, all_log
    )
