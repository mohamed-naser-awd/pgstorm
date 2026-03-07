"""Engine package - database connection and execution."""

from __future__ import annotations

from typing import Any

from pgstorm.engine.context import engine
from pgstorm.engine.create import create_engine
from pgstorm.engine.base import AsyncEngine, BaseEngine, SyncEngine
from pgstorm.engine.interface import EngineInterface


def transaction() -> Any:
    """
    Transaction context manager using the engine from context.
    Sync: ``with pgstorm.transaction():``
    Async: ``async with pgstorm.transaction():``
    """
    eng = engine.get()
    if eng is None:
        raise RuntimeError(
            "No engine set. Call create_engine() or engine.set(engine) before using pgstorm.transaction()."
        )
    return eng.transaction()


def set_search_path(*schemas: str, session: bool = False) -> Any:
    """
    Set the search_path using the engine from context.
    Must be called inside pgstorm.transaction().
    """
    eng = engine.get()
    if eng is None:
        raise RuntimeError(
            "No engine set. Call create_engine() or engine.set(engine) before using pgstorm.set_search_path()."
        )
    return eng.set_search_path(*schemas, session=session)


__all__ = [
    "engine",
    "create_engine",
    "transaction",
    "set_search_path",
    "BaseEngine",
    "SyncEngine",
    "AsyncEngine",
    "EngineInterface",
]
