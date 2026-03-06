"""Engine base classes - sync and async."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any

from pgstorm.engine.context import engine as engine_context_var

if TYPE_CHECKING:
    from pgstorm.engine.interface import EngineInterface
    from pgstorm.queryset.parser import CompiledQuery


class BaseEngine(ABC):
    """Base engine that delegates to an interface."""

    def __init__(self, interface: "EngineInterface") -> None:
        self._interface = interface

    @property
    def is_async(self) -> bool:
        return self._interface.is_async

    def execute(self, compiled: "CompiledQuery") -> Any:
        """
        Execute a compiled query. Returns rows or coroutine for async.
        Developer uses await when interface is async.
        """
        return self._interface.execute(compiled)

    def begin(self) -> Any:
        """Begin transaction. Returns coroutine for async."""
        return self._interface.begin()

    def commit(self) -> Any:
        """Commit transaction. Returns coroutine for async."""
        return self._interface.commit()

    def rollback(self) -> Any:
        """Rollback transaction. Returns coroutine for async."""
        return self._interface.rollback()

    def transaction(self) -> Any:
        """
        Context manager for transactions.
        Sync: use as `with engine.transaction():`
        Async: use as `async with engine.transaction():`
        """
        if self.is_async:
            return _AsyncTransactionContext(self)
        return _SyncTransactionContext(self)


class _SyncTransactionContext:
    def __init__(self, engine: BaseEngine) -> None:
        self._engine = engine

    def __enter__(self) -> BaseEngine:
        self._engine.begin()
        return self._engine

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is not None:
            self._engine.rollback()
        else:
            self._engine.commit()
        return False


class _AsyncTransactionContext:
    def __init__(self, engine: BaseEngine) -> None:
        self._engine = engine

    async def __aenter__(self) -> BaseEngine:
        await self._engine.begin()
        return self._engine

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is not None:
            await self._engine.rollback()
        else:
            await self._engine.commit()
        return False


class SyncEngine(BaseEngine):
    """Synchronous engine."""

    def get_engine(self) -> BaseEngine | None:
        """Get the current engine from context."""
        return engine_context_var.get()


class AsyncEngine(BaseEngine):
    """Asynchronous engine."""

    def get_engine(self) -> BaseEngine | None:
        """Get the current engine from context."""
        return engine_context_var.get()
