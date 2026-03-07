"""Engine base classes - sync and async."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, Union

from pgstorm.engine.context import engine as engine_context_var
from pgstorm.observers import (
    ObserverContext,
    notify,
    QUERY_AFTER_EXECUTE,
    QUERY_BEFORE_EXECUTE,
    RAW_SQL,
    TRANSACTION_BEGIN,
    TRANSACTION_COMMIT,
    TRANSACTION_ROLLBACK,
)

if TYPE_CHECKING:
    from pgstorm.engine.interface import EngineInterface
    from pgstorm.queryset.parser import CompiledQuery, RawQuery


class BaseEngine(ABC):
    """Base engine that delegates to an interface."""

    def __init__(self, interface: "EngineInterface") -> None:
        self._interface = interface

    @property
    def is_async(self) -> bool:
        return self._interface.is_async

    def execute(
        self, compiled: Union["CompiledQuery", "RawQuery"]
    ) -> Any:
        """
        Execute a compiled query. Returns rows or coroutine for async.
        Developer uses await when interface is async.
        """
        action = getattr(compiled, "action", "query")
        model = getattr(compiled, "model", None)
        table = getattr(compiled, "table", None)
        extra = getattr(compiled, "extra", None) or {}

        ctx_before = ObserverContext(
            action=QUERY_BEFORE_EXECUTE,
            model=model,
            table=table,
            compiled=compiled,
            params=getattr(compiled, "params", []),
            extra={"query_action": action, **extra},
        )
        notify(ctx_before)

        # Notify action-specific observers (fetch, create, update, delete, etc.)
        ctx_action_before = ObserverContext(
            action=action,
            model=model,
            table=table,
            compiled=compiled,
            params=getattr(compiled, "params", []),
            extra=extra,
        )
        notify(ctx_action_before)

        result = self._interface.execute(compiled)

        if self._interface.is_async:

            async def _execute_with_observers() -> Any:
                resolved = await result
                # Notify action-specific observers with result
                ctx_action_after = ObserverContext(
                    action=action,
                    model=model,
                    table=table,
                    compiled=compiled,
                    params=getattr(compiled, "params", []),
                    result=resolved,
                    extra=extra,
                )
                notify(ctx_action_after)
                ctx_after = ObserverContext(
                    action=QUERY_AFTER_EXECUTE,
                    model=model,
                    table=table,
                    compiled=compiled,
                    params=getattr(compiled, "params", []),
                    result=resolved,
                    extra={"query_action": action, **extra},
                )
                notify(ctx_after)
                return resolved

            return _execute_with_observers()

        # Notify action-specific observers with result
        ctx_action_after = ObserverContext(
            action=action,
            model=model,
            table=table,
            compiled=compiled,
            params=getattr(compiled, "params", []),
            result=result,
            extra=extra,
        )
        notify(ctx_action_after)
        ctx_after = ObserverContext(
            action=QUERY_AFTER_EXECUTE,
            model=model,
            table=table,
            compiled=compiled,
            params=getattr(compiled, "params", []),
            result=result,
            extra={"query_action": action, **extra},
        )
        notify(ctx_after)
        return result

    def raw_execute(self, query: str, params: list[Any] | None = None) -> Any:
        """
        Execute raw SQL. Returns rows or coroutine for async.
        Use %s placeholders in the query for parameters.
        """
        from pgstorm.queryset.parser import RawQuery

        raw = RawQuery(sql=query, params=params or [])
        return self.execute(raw)

    def begin(self) -> Any:
        """Begin transaction. Returns coroutine for async."""
        notify(ObserverContext(action=TRANSACTION_BEGIN))
        return self._interface.begin()

    def commit(self) -> Any:
        """Commit transaction. Returns coroutine for async."""
        result = self._interface.commit()
        if self._interface.is_async:

            async def _commit_with_observer() -> Any:
                await result
                notify(ObserverContext(action=TRANSACTION_COMMIT))
                return None

            return _commit_with_observer()
        notify(ObserverContext(action=TRANSACTION_COMMIT))
        return result

    def rollback(self) -> Any:
        """Rollback transaction. Returns coroutine for async."""
        result = self._interface.rollback()
        if self._interface.is_async:

            async def _rollback_with_observer() -> Any:
                await result
                notify(ObserverContext(action=TRANSACTION_ROLLBACK))
                return None

            return _rollback_with_observer()
        notify(ObserverContext(action=TRANSACTION_ROLLBACK))
        return result

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
