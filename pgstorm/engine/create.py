"""Factory for creating engines."""

from __future__ import annotations

from typing import Any, Type, Union

from pgstorm.engine.context import engine as engine_context_var
from pgstorm.engine.base import AsyncEngine, BaseEngine, SyncEngine
from pgstorm.engine.interface import EngineInterface

# Built-in interface types
INTERFACE_MAP = {
    "psycopg2": "pgstorm.engine.interfaces.psycopg2.Psycopg2Interface",
    "psycopg3": "pgstorm.engine.interfaces.psycopg3_sync.Psycopg3SyncInterface",
    "psycopg3_sync": "pgstorm.engine.interfaces.psycopg3_sync.Psycopg3SyncInterface",
    "psycopg3_async": "pgstorm.engine.interfaces.psycopg3_async.Psycopg3AsyncInterface",
    "asyncpg": "pgstorm.engine.interfaces.asyncpg.AsyncpgInterface",
}


def _resolve_interface(
    interface: Union[str, Type[EngineInterface]], conninfo: Union[str, dict[str, Any]], **kwargs: Any
) -> EngineInterface:
    """Resolve interface from string or class to an instance."""
    if isinstance(interface, type) and issubclass(interface, EngineInterface):
        return interface(conninfo, **kwargs)
    if isinstance(interface, str):
        path = INTERFACE_MAP.get(interface)
        if path is None:
            raise ValueError(
                f"Unknown interface {interface!r}. "
                f"Choose from: {list(INTERFACE_MAP.keys())}, or pass an EngineInterface subclass."
            )
        module_path, class_name = path.rsplit(".", 1)
        import importlib

        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        return cls(conninfo, **kwargs)
    raise TypeError(
        "interface must be a string (e.g. 'psycopg3', 'asyncpg') "
        "or an EngineInterface subclass"
    )


def create_engine(
    conninfo: Union[str, dict[str, Any]],
    interface: Union[str, Type[EngineInterface]] = "psycopg3",
    *,
    set_global: bool = True,
    **kwargs: Any,
) -> BaseEngine:
    """
    Create an engine and optionally set it in the context var.

    Args:
        conninfo: Passed as-is to the interface. Typically a PostgreSQL connection string
            or dict of connection params. Each interface handles conninfo according to
            its driver's requirements (schema, options, etc.).
        interface: One of "psycopg2", "psycopg3", "psycopg3_async", "asyncpg",
            or a custom EngineInterface subclass.
        set_global: If True (default), set the engine in the context var so querysets
            use it automatically.
        **kwargs: Passed to the interface constructor (e.g. for connection options).

    Returns:
        SyncEngine or AsyncEngine depending on the interface.
    """
    iface = _resolve_interface(interface, conninfo, **kwargs)
    eng: BaseEngine
    if iface.is_async:
        eng = AsyncEngine(iface)
    else:
        eng = SyncEngine(iface)
    if set_global:
        engine_context_var.set(eng)
    return eng
