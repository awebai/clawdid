from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pgdbm import AsyncDatabaseManager, DatabaseConfig

from clawdid.config import settings
from clawdid.db import DatabaseInfra
from clawdid.ratelimit import build_rate_limiter
from clawdid.routes.did import router as did_router
from clawdid.routes.ops import router as ops_router

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_config = DatabaseConfig(
        connection_string=settings.database_url,
        min_connections=settings.database_pool_size,
        max_connections=settings.database_pool_size + settings.database_pool_overflow,
        schema=None,
    )

    shared_pool = await AsyncDatabaseManager.create_shared_pool(db_config)
    infra = DatabaseInfra()
    await infra.initialize(shared_pool=shared_pool)

    app.state.db = infra
    app.state.pool = shared_pool
    redis = None
    if settings.rate_limit_enabled and settings.rate_limit_backend == "redis":
        if not settings.rate_limit_redis_url:
            raise ValueError(
                "rate_limit_backend=redis requires RATE_LIMIT_REDIS_URL/REDIS_URL"
            )
        from redis.asyncio import Redis

        redis = Redis.from_url(settings.rate_limit_redis_url)
        app.state.redis = redis
    else:
        app.state.redis = None
    app.state.rate_limiter = build_rate_limiter(redis=redis)
    yield
    if app.state.redis is not None:
        await app.state.redis.close()
    await infra.close()
    await shared_pool.close()


def create_app() -> FastAPI:
    _configure_logging()
    app = FastAPI(
        title="clawdid",
        version=os.environ.get("CLAWDID_RELEASE_TAG", "dev"),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ops_router)
    app.include_router(did_router)
    # Compatibility: allow both `/did/...` and `/v1/did/...` for clients that
    # standardize on aweb-style versioned routing.
    app.include_router(did_router, prefix="/v1")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "clawdid.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        proxy_headers=True,
    )
