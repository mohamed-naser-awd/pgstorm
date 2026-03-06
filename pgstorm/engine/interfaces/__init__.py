"""Built-in database driver interfaces."""

from __future__ import annotations

from pgstorm.engine.interfaces.psycopg2 import Psycopg2Interface
from pgstorm.engine.interfaces.psycopg3_sync import Psycopg3SyncInterface
from pgstorm.engine.interfaces.psycopg3_async import Psycopg3AsyncInterface
from pgstorm.engine.interfaces.asyncpg import AsyncpgInterface

__all__ = [
    "Psycopg2Interface",
    "Psycopg3SyncInterface",
    "Psycopg3AsyncInterface",
    "AsyncpgInterface",
]
