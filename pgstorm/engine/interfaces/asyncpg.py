"""asyncpg driver interface."""

from __future__ import annotations

from typing import Any, Union

from pgstorm.engine.interface import CompiledOrRaw, EngineInterface
from pgstorm.engine.query_utils import composable_to_plain, to_asyncpg_format
from pgstorm.observers import CONNECTION_OPEN, ObserverContext, notify
from pgstorm.queryset.parser import RawQuery


class AsyncpgInterface(EngineInterface):
    """Async interface using asyncpg."""

    def __init__(self, conninfo: Union[str, dict[str, Any]], **kwargs: Any) -> None:
        self._conninfo = conninfo
        self._kwargs = kwargs
        self._conn: Any = None

    @property
    def is_async(self) -> bool:
        return True

    def _connect_args(self) -> tuple[Any, dict[str, Any]]:
        """Return (positional_args, kwargs) for asyncpg.connect."""
        merged = {**self._kwargs}
        if isinstance(self._conninfo, str):
            return (self._conninfo, merged)
        # Dict: asyncpg uses 'database' not 'dbname', 'user' not 'username'
        params = dict(self._conninfo)
        if "dbname" in params and "database" not in params:
            params["database"] = params.pop("dbname")
        if "username" in params and "user" not in params:
            params["user"] = params.pop("username")
        merged.update(params)
        return ((), merged)

    async def _get_conn(self) -> Any:
        if self._conn is None or self._conn.is_closed():
            import asyncpg
            args, kwargs = self._connect_args()
            if args:
                self._conn = await asyncpg.connect(args[0], **kwargs)
            else:
                self._conn = await asyncpg.connect(**kwargs)
            notify(ObserverContext(action=CONNECTION_OPEN, extra={"connection": self._conn}))
        return self._conn

    async def execute(self, compiled: CompiledOrRaw) -> list[dict[str, Any]]:
        if isinstance(compiled, RawQuery):
            query_str, params = compiled.sql, compiled.params
            query_str, params = to_asyncpg_format(query_str, params)
        else:
            query_str, params = composable_to_plain(compiled.sql, compiled.params)
            query_str, params = to_asyncpg_format(query_str, params)
        conn = await self._get_conn()
        rows = await conn.fetch(query_str, *params)
        return [dict(row) for row in rows]

    async def begin(self) -> None:
        conn = await self._get_conn()
        await conn.execute("ROLLBACK")  # Clear any previous state

    async def commit(self) -> None:
        conn = await self._get_conn()
        await conn.execute("COMMIT")

    async def rollback(self) -> None:
        conn = await self._get_conn()
        await conn.execute("ROLLBACK")
