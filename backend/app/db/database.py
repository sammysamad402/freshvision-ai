"""
FreshVision AI — Database layer.

Supports two backends transparently:
  • SQLite   (local dev)   — set DATABASE_URL=sqlite+aiosqlite:///./storage/freshvision.db
  • PostgreSQL (production) — set DATABASE_URL=postgresql+asyncpg://user:pass@host/db

Railway / Supabase / Render all provide a DATABASE_URL env var automatically.
If DATABASE_URL is not set, falls back to the local SQLite file.
"""
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncConnection

from app.core.config import DB_PATH

logger = logging.getLogger("freshvision.db")

# ── Engine factory ────────────────────────────────────────────────────────────
def _normalize_pg_url(url: str) -> str:
    """
    Force any postgres/postgresql URL onto the asyncpg driver.

    Providers hand out connection strings in several shapes:
      postgres://...                Railway / Render / Heroku style
      postgresql://...              Supabase / most standard tools
      postgresql+psycopg2://...     some ORMs/tools default to this

    None of these work with create_async_engine unless the dialect explicitly
    says "+asyncpg", so we always rewrite the scheme instead of only handling
    the "postgres://" case. This is what previously caused
    ModuleNotFoundError: No module named 'psycopg2' on Hugging Face Spaces /
    Supabase deployments — SQLAlchemy silently picked the sync psycopg2 dialect
    (which isn't installed) instead of asyncpg.
    """
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    base_scheme = scheme.split("+")[0]
    if base_scheme in ("postgres", "postgresql"):
        return f"postgresql+asyncpg://{rest}"
    return url


def _make_engine() -> AsyncEngine:
    url = _normalize_pg_url(os.getenv("DATABASE_URL", ""))

    if url.startswith("postgresql"):
        logger.info("Database backend: PostgreSQL")
        return create_async_engine(
            url, pool_size=5, max_overflow=10, pool_pre_ping=True, echo=False
        )

    # Default: SQLite (local dev or Docker without DATABASE_URL)
    sqlite_url = f"sqlite+aiosqlite:///{DB_PATH}"
    logger.info("Database backend: SQLite at %s", DB_PATH)
    return create_async_engine(sqlite_url, connect_args={"check_same_thread": False}, echo=False)


_engine: Optional[AsyncEngine] = None

def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


# ── Schema ────────────────────────────────────────────────────────────────────
_SCHEMA_SQLITE = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'inspector',
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS inspections (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id        TEXT UNIQUE NOT NULL,
    owner_username        TEXT NOT NULL DEFAULT '',
    timestamp            TEXT NOT NULL,
    warehouse_id         TEXT,
    supplier_id          TEXT,
    image_path           TEXT,
    overlay_path         TEXT,
    storage_temp_c       REAL,
    storage_humidity_pct REAL,
    item_count           INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS inspection_items (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id        TEXT NOT NULL REFERENCES inspections(inspection_id),
    item_id              TEXT NOT NULL,
    product_type         TEXT,
    detection_confidence REAL,
    defect_coverage_pct  REAL,
    quality_grade        TEXT,
    quality_score        REAL,
    freshness_label      TEXT,
    freshness_pct        REAL,
    shelf_life_days      REAL,
    decision             TEXT,
    decision_reasons     TEXT,
    defects              TEXT,
    explanation          TEXT
);
CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    username  TEXT,
    action    TEXT,
    detail    TEXT
);
CREATE INDEX IF NOT EXISTS idx_insp_ts     ON inspections(timestamp);
CREATE INDEX IF NOT EXISTS idx_insp_owner  ON inspections(owner_username);
CREATE INDEX IF NOT EXISTS idx_items_grade ON inspection_items(quality_grade);
"""

_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'inspector',
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS inspections (
    id                   SERIAL PRIMARY KEY,
    inspection_id        TEXT UNIQUE NOT NULL,
    owner_username        TEXT NOT NULL DEFAULT '',
    timestamp            TEXT NOT NULL,
    warehouse_id         TEXT,
    supplier_id          TEXT,
    image_path           TEXT,
    overlay_path         TEXT,
    storage_temp_c       FLOAT,
    storage_humidity_pct FLOAT,
    item_count           INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS inspection_items (
    id                   SERIAL PRIMARY KEY,
    inspection_id        TEXT NOT NULL REFERENCES inspections(inspection_id),
    item_id              TEXT NOT NULL,
    product_type         TEXT,
    detection_confidence FLOAT,
    defect_coverage_pct  FLOAT,
    quality_grade        TEXT,
    quality_score        FLOAT,
    freshness_label      TEXT,
    freshness_pct        FLOAT,
    shelf_life_days      FLOAT,
    decision             TEXT,
    decision_reasons     TEXT,
    defects              TEXT,
    explanation          TEXT
);
CREATE TABLE IF NOT EXISTS audit_log (
    id        SERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    username  TEXT,
    action    TEXT,
    detail    TEXT
);
CREATE INDEX IF NOT EXISTS idx_insp_ts     ON inspections(timestamp);
CREATE INDEX IF NOT EXISTS idx_insp_owner  ON inspections(owner_username);
CREATE INDEX IF NOT EXISTS idx_items_grade ON inspection_items(quality_grade);
"""


def _is_postgres() -> bool:
    url = os.getenv("DATABASE_URL", "")
    return "postgres" in url


def _ph(n: int) -> str:
    """Placeholder: $N for PostgreSQL, ? for SQLite."""
    return f"${n}" if _is_postgres() else "?"


async def init_db() -> None:
    engine = get_engine()
    schema = _SCHEMA_PG if _is_postgres() else _SCHEMA_SQLITE
    async with engine.begin() as conn:
        if _is_postgres():
            for stmt in [s.strip() for s in schema.split(";") if s.strip()]:
                await conn.execute(text(stmt))
        else:
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA foreign_keys=ON"))
            for stmt in [s.strip() for s in schema.split(";") if s.strip()
                         and not s.strip().startswith("PRAGMA")]:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    pass

        # Migration: older deployments may already have an `inspections` table
        # without the owner_username column (added for per-user data privacy).
        try:
            await conn.execute(text(
                "ALTER TABLE inspections ADD COLUMN owner_username TEXT NOT NULL DEFAULT ''"
            ))
            logger.info("Migrated inspections table: added owner_username column")
        except Exception:
            pass  # column already exists

        # Seed default demo users if empty — only when explicitly enabled.
        from app.core.config import SEED_DEMO_USERS
        result = await conn.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        if count == 0 and SEED_DEMO_USERS:
            from passlib.context import CryptContext
            try:
                _pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
                _pwd.hash("probe")
            except Exception:
                _pwd = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
            now = datetime.utcnow().isoformat()
            for uname, pw, role in [
                ("admin",     "freshvision2024", "admin"),
                ("inspector", "inspect123",      "inspector"),
            ]:
                if _is_postgres():
                    await conn.execute(text(
                        "INSERT INTO users (username,password_hash,role,created_at) "
                        "VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING"
                    ), {"1": uname, "2": _pwd.hash(pw), "3": role, "4": now})
                else:
                    await conn.execute(text(
                        "INSERT OR IGNORE INTO users (username,password_hash,role,created_at) "
                        "VALUES (:u,:p,:r,:c)"
                    ), {"u": uname, "p": _pwd.hash(pw), "r": role, "c": now})
    logger.info("Database initialised  backend=%s", "postgres" if _is_postgres() else "sqlite")


# ── CRUD helpers ──────────────────────────────────────────────────────────────

async def save_inspection(result: Dict[str, Any], image_path: str, overlay_path: str,
                           warehouse_id: str = None, supplier_id: str = None,
                           owner_username: str = "") -> None:
    ts = result["timestamp"]
    ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
    engine = get_engine()
    async with engine.begin() as conn:
        if _is_postgres():
            await conn.execute(text("""
                INSERT INTO inspections
                  (inspection_id,owner_username,timestamp,warehouse_id,supplier_id,image_path,
                   overlay_path,storage_temp_c,storage_humidity_pct,item_count)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) ON CONFLICT DO NOTHING
            """), {"1": result["inspection_id"], "2": owner_username, "3": ts_str, "4": warehouse_id,
                   "5": supplier_id, "6": image_path, "7": overlay_path,
                   "8": result.get("storage_temp_c"), "9": result.get("storage_humidity_pct"),
                   "10": len(result["items"])})
        else:
            await conn.execute(text("""
                INSERT OR IGNORE INTO inspections
                  (inspection_id,owner_username,timestamp,warehouse_id,supplier_id,image_path,
                   overlay_path,storage_temp_c,storage_humidity_pct,item_count)
                VALUES (:iid,:own,:ts,:wh,:sup,:ip,:op,:temp,:hum,:cnt)
            """), {"iid": result["inspection_id"], "own": owner_username, "ts": ts_str, "wh": warehouse_id,
                   "sup": supplier_id, "ip": image_path, "op": overlay_path,
                   "temp": result.get("storage_temp_c"), "hum": result.get("storage_humidity_pct"),
                   "cnt": len(result["items"])})

        for item in result["items"]:
            if _is_postgres():
                await conn.execute(text("""
                    INSERT INTO inspection_items
                      (inspection_id,item_id,product_type,detection_confidence,
                       defect_coverage_pct,quality_grade,quality_score,
                       freshness_label,freshness_pct,shelf_life_days,
                       decision,decision_reasons,defects,explanation)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                """), {"1": result["inspection_id"], "2": item["item_id"],
                       "3": item["product_type"], "4": item["detection_confidence"],
                       "5": item["defect_coverage_pct"], "6": item["quality_grade"],
                       "7": item["quality_score"], "8": item["freshness_label"],
                       "9": item["freshness_pct"], "10": item["shelf_life_days"],
                       "11": item["decision"], "12": json.dumps(item["decision_reasons"]),
                       "13": json.dumps(item["defects"]), "14": item["explanation"]})
            else:
                await conn.execute(text("""
                    INSERT INTO inspection_items
                      (inspection_id,item_id,product_type,detection_confidence,
                       defect_coverage_pct,quality_grade,quality_score,
                       freshness_label,freshness_pct,shelf_life_days,
                       decision,decision_reasons,defects,explanation)
                    VALUES (:iid,:itid,:pt,:dc,:dcp,:qg,:qs,:fl,:fp,:sl,:dec,:dr,:def,:exp)
                """), {"iid": result["inspection_id"], "itid": item["item_id"],
                       "pt": item["product_type"], "dc": item["detection_confidence"],
                       "dcp": item["defect_coverage_pct"], "qg": item["quality_grade"],
                       "qs": item["quality_score"], "fl": item["freshness_label"],
                       "fp": item["freshness_pct"], "sl": item["shelf_life_days"],
                       "dec": item["decision"], "dr": json.dumps(item["decision_reasons"]),
                       "def": json.dumps(item["defects"]), "exp": item["explanation"]})


async def get_inspections(limit=50, offset=0, warehouse_id=None, supplier_id=None,
                           owner_username=None):
    filters, params = [], {}
    if owner_username:
        filters.append("owner_username = :own"); params["own"] = owner_username
    if warehouse_id:
        filters.append("warehouse_id = :wh"); params["wh"] = warehouse_id
    if supplier_id:
        filters.append("supplier_id = :sup"); params["sup"] = supplier_id
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params["lim"] = limit; params["off"] = offset
    async with get_engine().connect() as conn:
        r = await conn.execute(text(
            f"SELECT * FROM inspections {where} ORDER BY timestamp DESC LIMIT :lim OFFSET :off"
        ), params)
        return [dict(row._mapping) for row in r.fetchall()]


async def get_inspection_detail(inspection_id: str, owner_username: Optional[str] = None):
    """
    If `owner_username` is given, the row is only returned when it belongs to
    that user (pass None — e.g. for admins — to fetch regardless of owner).
    """
    async with get_engine().connect() as conn:
        r = await conn.execute(
            text("SELECT * FROM inspections WHERE inspection_id=:iid"), {"iid": inspection_id})
        row = r.fetchone()
        if not row:
            return None
        insp = dict(row._mapping)
        if owner_username is not None and insp.get("owner_username") != owner_username:
            return None
        r2 = await conn.execute(
            text("SELECT * FROM inspection_items WHERE inspection_id=:iid"), {"iid": inspection_id})
        items = []
        for item_row in r2.fetchall():
            it = dict(item_row._mapping)
            it["defects"]          = json.loads(it.get("defects") or "[]")
            it["decision_reasons"] = json.loads(it.get("decision_reasons") or "[]")
            items.append(it)
        insp["items"] = items
        return insp


async def get_analytics(days=30, warehouse_id=None, supplier_id=None, owner_username=None):
    if _is_postgres():
        cutoff_expr = f"NOW() - INTERVAL '{days} days'"
        date_fn     = "DATE(timestamp::timestamp)"
    else:
        cutoff_expr = f"datetime('now', '-{days} days')"
        date_fn     = "DATE(timestamp)"

    def _esc(v: str) -> str:
        return v.replace("'", "''")

    extra = ""
    if owner_username: extra += f" AND i.owner_username='{_esc(owner_username)}'"
    if warehouse_id: extra += f" AND i.warehouse_id='{_esc(warehouse_id)}'"
    if supplier_id:  extra += f" AND i.supplier_id='{_esc(supplier_id)}'"

    async with get_engine().connect() as conn:
        async def q(sql): return (await conn.execute(text(sql))).fetchall()

        grade_rows    = await q(f"SELECT it.quality_grade,COUNT(*) cnt FROM inspection_items it JOIN inspections i USING(inspection_id) WHERE i.timestamp>={cutoff_expr} {extra} GROUP BY it.quality_grade")
        fresh_rows    = await q(f"SELECT it.freshness_label,COUNT(*) cnt FROM inspection_items it JOIN inspections i USING(inspection_id) WHERE i.timestamp>={cutoff_expr} {extra} GROUP BY it.freshness_label")
        decision_rows = await q(f"SELECT it.decision,COUNT(*) cnt FROM inspection_items it JOIN inspections i USING(inspection_id) WHERE i.timestamp>={cutoff_expr} {extra} GROUP BY it.decision")
        agg_row       = (await q(f"SELECT COUNT(DISTINCT i.inspection_id) ti,COUNT(it.id) total,AVG(it.defect_coverage_pct) avg_def,SUM(CASE WHEN it.decision='Reject' THEN 1 ELSE 0 END) rej FROM inspection_items it JOIN inspections i USING(inspection_id) WHERE i.timestamp>={cutoff_expr} {extra}"))[0]
        trend_rows    = await q(f"SELECT {date_fn} day,COUNT(it.id) cnt,AVG(it.quality_score) avg_quality FROM inspection_items it JOIN inspections i USING(inspection_id) WHERE i.timestamp>={cutoff_expr} {extra} GROUP BY {date_fn} ORDER BY {date_fn} DESC LIMIT 14")
        sup_rows      = await q(f"SELECT i.supplier_id,COUNT(it.id) total,AVG(it.quality_score) avg_quality,SUM(CASE WHEN it.decision='Reject' THEN 1 ELSE 0 END) rejected FROM inspection_items it JOIN inspections i USING(inspection_id) WHERE i.timestamp>={cutoff_expr} {extra} AND i.supplier_id IS NOT NULL GROUP BY i.supplier_id")

    def safe(v): return float(v) if v is not None else 0.0
    return {
        "total_inspections":      int(agg_row[0] or 0),
        "total_items":            int(agg_row[1] or 0),
        "avg_defect_coverage_pct": round(safe(agg_row[2]), 2),
        "rejected_count":          int(agg_row[3] or 0),
        "grade_distribution":     {r[0]: int(r[1]) for r in grade_rows},
        "freshness_distribution": {r[0]: int(r[1]) for r in fresh_rows},
        "decision_distribution":  {r[0]: int(r[1]) for r in decision_rows},
        "recent_trend":           [{"day": str(r[0]), "cnt": int(r[1]), "avg_quality": round(safe(r[2]),1)} for r in trend_rows],
        "by_supplier":            {r[0]: {"total": int(r[1]), "avg_quality": round(safe(r[2]),1), "rejected": int(r[3])} for r in sup_rows},
        "by_warehouse":           {},
    }


async def get_user(username: str):
    async with get_engine().connect() as conn:
        r = await conn.execute(
            text("SELECT * FROM users WHERE username=:u"), {"u": username})
        row = r.fetchone()
        return dict(row._mapping) if row else None


class UsernameTakenError(Exception):
    """Raised when attempting to register a username that already exists."""


async def create_user(username: str, password_hash: str, role: str = "inspector") -> dict:
    """
    Create a brand-new user account. Each account is fully isolated — its
    inspections, history, and analytics are never visible to other
    non-admin accounts.
    """
    now = datetime.utcnow().isoformat()
    engine = get_engine()
    async with engine.begin() as conn:
        existing = await conn.execute(
            text("SELECT id FROM users WHERE username=:u"), {"u": username})
        if existing.fetchone():
            raise UsernameTakenError(username)
        if _is_postgres():
            await conn.execute(text(
                "INSERT INTO users (username,password_hash,role,created_at) "
                "VALUES ($1,$2,$3,$4)"
            ), {"1": username, "2": password_hash, "3": role, "4": now})
        else:
            await conn.execute(text(
                "INSERT INTO users (username,password_hash,role,created_at) "
                "VALUES (:u,:p,:r,:c)"
            ), {"u": username, "p": password_hash, "r": role, "c": now})
    return await get_user(username)


async def log_audit(username: str, action: str, detail: str = "") -> None:
    async with get_engine().begin() as conn:
        await conn.execute(text(
            "INSERT INTO audit_log (timestamp,username,action,detail) VALUES (:ts,:u,:a,:d)"
        ), {"ts": datetime.utcnow().isoformat(), "u": username, "a": action, "d": detail})
