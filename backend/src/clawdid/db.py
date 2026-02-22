from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import Request
from pgdbm import AsyncDatabaseManager, DatabaseConfig
from pgdbm.migrations import AsyncMigrationManager


class DatabaseInfra:
    """Shared pgdbm infrastructure for clawdid (single schema: clawdid)."""

    def __init__(self) -> None:
        self._shared_pool: Optional[Any] = None
        self._db: Optional[AsyncDatabaseManager] = None
        self._initialized: bool = False
        self._init_lock: asyncio.Lock = asyncio.Lock()
        self._owns_pool: bool = True

    async def initialize(self, *, shared_pool: Optional[Any] = None) -> None:
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            if shared_pool is None:
                database_url = os.environ.get("DATABASE_URL")
                if not database_url:
                    raise RuntimeError(
                        "DATABASE_URL must be set to initialize clawdid DB"
                    )
                config = DatabaseConfig(connection_string=database_url, schema=None)
                shared_pool = await AsyncDatabaseManager.create_shared_pool(config)
                self._owns_pool = True
            else:
                self._owns_pool = False

            self._shared_pool = shared_pool
            self._db = AsyncDatabaseManager(pool=shared_pool, schema="clawdid")

            await self._db.execute('CREATE SCHEMA IF NOT EXISTS "clawdid"')

            base_dir = Path(__file__).resolve().parent
            migrations_root = base_dir / "migrations" / "clawdid"
            if migrations_root.is_dir():
                manager = AsyncMigrationManager(
                    self._db,
                    migrations_path=str(migrations_root),
                    module_name="clawdid",
                )
                await manager.apply_pending_migrations()

            self._initialized = True

    async def close(self) -> None:
        if self._shared_pool is not None and self._owns_pool:
            await self._shared_pool.close()
        self._db = None
        self._shared_pool = None
        self._initialized = False
        self._owns_pool = True

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def manager(self) -> AsyncDatabaseManager:
        if not self._initialized or self._db is None:
            raise RuntimeError("DatabaseInfra is not initialized")
        return self._db


db_infra = DatabaseInfra()


def get_db_infra(request: Request) -> DatabaseInfra:
    return request.app.state.db
