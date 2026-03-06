"""psycopg3 sync driver interface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union

from pgstorm.engine.interface import EngineInterface

if TYPE_CHECKING:
    from pgstorm.queryset.parser import CompiledQuery


class Psycopg3SyncInterface(EngineInterface):
    """Sync interface using psycopg (v3)."""

    def __init__(self, conninfo: Union[str, dict[str, Any]], **kwargs: Any) -> None:
        self._conninfo = conninfo
        self._kwargs = kwargs
        self._conn: Any = None

    @property
    def is_async(self) -> bool:
        return False

    def _get_conn(self) -> Any:
        if self._conn is None or self._conn.closed:
            import psycopg
            if isinstance(self._conninfo, str):
                self._conn = psycopg.connect(self._conninfo, **self._kwargs)
            else:
                self._conn = psycopg.connect(conninfo="", **{**self._conninfo, **self._kwargs})
        return self._conn

    def execute(self, compiled: "CompiledQuery") -> list[Any]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(compiled.sql, compiled.params)
            if cur.description:
                columns = [d.name for d in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        return []

    def begin(self) -> None:
        self._get_conn().rollback()  # Clear any previous state

    def commit(self) -> None:
        self._get_conn().commit()

    def rollback(self) -> None:
        self._get_conn().rollback()
