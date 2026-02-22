from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from clawdid.build_info import release_identity
from clawdid.db import DatabaseInfra, get_db_infra

router = APIRouter()


@router.get("/live")
async def live() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(db_infra: DatabaseInfra = Depends(get_db_infra)) -> dict:
    try:
        db = db_infra.manager()
        await db.fetch_value("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"database disconnected: {e}"
        ) from e


@router.get("/meta")
async def meta() -> dict:
    return {"service": "clawdid", **release_identity().to_dict()}


@router.get("/health")
async def health(db_infra: DatabaseInfra = Depends(get_db_infra)) -> dict:
    now = datetime.now(timezone.utc)
    checks: dict[str, str] = {}
    status = "ok"
    try:
        db = db_infra.manager()
        await db.fetch_value("SELECT 1")
        checks["database"] = "connected"
    except Exception:
        checks["database"] = "disconnected"
        status = "degraded"
    return {
        "status": status,
        "time": now.isoformat(),
        "release": release_identity().to_dict(),
        "checks": checks,
    }


@router.get("/api/v1/release")
async def release() -> dict:
    return release_identity().to_dict()
