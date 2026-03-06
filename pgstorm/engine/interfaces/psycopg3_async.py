"""psycopg3 async driver interface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union

from pgstorm.engine.interface import EngineInterface

if TYPE_CHECKING:
    from pgstorm.queryset.parser import CompiledQuery


class Psycopg3AsyncInterface(EngineInterface):
    """Async interface using psycopg (v3) async."""

    def __init__(self, conninfo: Union[str, dict[str, Any]], **kwargs: Any) -> None:
        self._conninfo = conninfo
        self._kwargs = kwargs
        self._conn: Any = None

    @property
    def is_async(self) -> bool:
        return True

    async def _get_conn(self) -> Any:
        if self._conn is None or self._conn.closed:
            import psycopg
            if isinstance(self._conninfo, str):
                self._conn = await psycopg.AsyncConnection.connect(
                    self._conninfo, **self._kwargs
                )
            else:
                self._conn = await psycopg.AsyncConnection.connect(
                    conninfo="", **{**self._conninfo, **self._kwargs}
                )
        return self._conn

    async def execute(self, compiled: "CompiledQuery") -> list[Any]:
        conn = await self._get_conn()
        async with conn.cursor() as cur:
            await cur.execute(compiled.sql, compiled.params)
            if cur.description:
                columns = [d.name for d in cur.description]
                rows = await cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        return []

    async def begin(self) -> None:
        conn = await self._get_conn()
        await conn.rollback()  # Clear any previous state

    async def commit(self) -> None:
        conn = await self._get_conn()
        await conn.commit()

    async def rollback(self) -> None:
        conn = await self._get_conn()
        await conn.rollback()
