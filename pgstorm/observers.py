"""
Observer pattern for pgstorm ORM hooks.

Register observers for various database operations. Table-specific observers
are filtered by the registry—no model checking needed in your callbacks.

  @pgstorm.observers(action="fetch")
  def on_fetch(ctx):
      print(f"Fetched from {ctx.table}")

  @pgstorm.table_observers(action="post_save", table=User)
  def on_user_saved(ctx):
      # Only called for User model, after save—no model check needed
      print(f"Saved user: {ctx.extra.get('instance')}")

Django-style actions: pre_save, post_save, pre_delete, post_delete,
  pre_create, post_create, pre_update, post_update, etc.

Also: fetch, raw_sql, connection_open, connection_close, cursor_open,
  cursor_close, query_before_execute, query_after_execute,
  transaction_begin, transaction_commit, transaction_rollback
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Type

# Type for observer callback - use this to type your observer functions
# Callbacks can be sync or async; notify_async will await async callbacks
ObserverCallback = Callable[["ObserverContext"], None]

# Optional per-observer filter. If provided, the callback is only invoked when
# the filter returns True for the current context. This allows filtering by
# arbitrary flags (for example, values in ctx.extra) or any other context
# attributes in addition to the action/table matching done by the registry.
ObserverFilter = Callable[["ObserverContext"], bool]

# Valid observer actions (for type hints)
ObserverAction = Literal[
    "fetch",
    "pre_save",
    "post_save",
    "pre_create",
    "post_create",
    "pre_bulk_create",
    "post_bulk_create",
    "pre_update",
    "post_update",
    "pre_bulk_update",
    "post_bulk_update",
    "pre_delete",
    "post_delete",
    "raw_sql",
    "connection_open",
    "connection_close",
    "cursor_open",
    "cursor_close",
    "query_before_execute",
    "query_after_execute",
    "transaction_begin",
    "transaction_commit",
    "transaction_rollback",
]

# Action constants for observers (Django-style pre/post)
FETCH = "fetch"
PRE_SAVE = "pre_save"
POST_SAVE = "post_save"
PRE_CREATE = "pre_create"
POST_CREATE = "post_create"
PRE_BULK_CREATE = "pre_bulk_create"
POST_BULK_CREATE = "post_bulk_create"
PRE_UPDATE = "pre_update"
POST_UPDATE = "post_update"
PRE_BULK_UPDATE = "pre_bulk_update"
POST_BULK_UPDATE = "post_bulk_update"
PRE_DELETE = "pre_delete"
POST_DELETE = "post_delete"
RAW_SQL = "raw_sql"
CONNECTION_OPEN = "connection_open"
CONNECTION_CLOSE = "connection_close"
CURSOR_OPEN = "cursor_open"
CURSOR_CLOSE = "cursor_close"
QUERY_BEFORE_EXECUTE = "query_before_execute"
QUERY_AFTER_EXECUTE = "query_after_execute"
TRANSACTION_BEGIN = "transaction_begin"
TRANSACTION_COMMIT = "transaction_commit"
TRANSACTION_ROLLBACK = "transaction_rollback"

# Map from query action -> pre/post action names (for observer_runner)
_QUERY_ACTION_TO_PRE: dict[str, str] = {
    "create": PRE_CREATE,
    "bulk_create": PRE_BULK_CREATE,
    "update": PRE_UPDATE,
    "bulk_update": PRE_BULK_UPDATE,
    "delete": PRE_DELETE,
}
_QUERY_ACTION_TO_POST: dict[str, str] = {
    "create": POST_CREATE,
    "bulk_create": POST_BULK_CREATE,
    "update": POST_UPDATE,
    "bulk_update": POST_BULK_UPDATE,
    "delete": POST_DELETE,
}

# All actions that can be observed
ALL_ACTIONS = frozenset({
    FETCH,
    PRE_SAVE,
    POST_SAVE,
    PRE_CREATE,
    POST_CREATE,
    PRE_BULK_CREATE,
    POST_BULK_CREATE,
    PRE_UPDATE,
    POST_UPDATE,
    PRE_BULK_UPDATE,
    POST_BULK_UPDATE,
    PRE_DELETE,
    POST_DELETE,
    RAW_SQL,
    CONNECTION_OPEN,
    CONNECTION_CLOSE,
    CURSOR_OPEN,
    CURSOR_CLOSE,
    QUERY_BEFORE_EXECUTE,
    QUERY_AFTER_EXECUTE,
    TRANSACTION_BEGIN,
    TRANSACTION_COMMIT,
    TRANSACTION_ROLLBACK,
})


@dataclass
class ObserverContext:
    """Context passed to observer callbacks."""

    action: str
    model: type[Any] | None = None
    table: str | None = None
    compiled: Any = None  # CompiledQuery or None for non-query actions
    params: list[Any] = field(default_factory=list)
    result: Any = None  # Set for query_after_execute
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class _ObserverEntry:
    action: str
    callback: ObserverCallback
    table: type[Any] | None = None  # None = global, else table-specific
    observer_filter: ObserverFilter | None = None


class ObserverRegistry:
    """Registry for global and table-specific observers."""

    def __init__(self) -> None:
        self._observers: list[_ObserverEntry] = []

    def _iter_results(self, ctx: ObserverContext):
        """Yield callback results for observers matching the context's action and table."""
        for entry in self._observers:
            if entry.action != ctx.action:
                continue
            if entry.table is not None:
                if ctx.model is None or not issubclass(ctx.model, entry.table):
                    continue
            if entry.observer_filter is not None and not entry.observer_filter(ctx):
                continue
            yield entry.callback(ctx)

    def register(
        self,
        action: str,
        callback: ObserverCallback,
        table: type[Any] | None = None,
        observer_filter: ObserverFilter | None = None,
    ) -> None:
        if action not in ALL_ACTIONS:
            raise ValueError(
                f"Unknown action {action!r}. Valid actions: {sorted(ALL_ACTIONS)}"
            )
        self._observers.append(
            _ObserverEntry(
                action=action,
                callback=callback,
                table=table,
                observer_filter=observer_filter,
            )
        )

    def notify(self, ctx: ObserverContext) -> None:
        """Call all observers matching the context's action and table."""
        try:
            for result in self._iter_results(ctx):
                if result is not None and asyncio.iscoroutine(result):
                    raise RuntimeError(
                        "Async observer used with sync engine. Use async engine (create_engine(..., interface='asyncpg')) "
                        "or register a sync observer."
                    )
        except Exception:
            raise  # Let observers propagate their errors

    async def notify_async(self, ctx: ObserverContext) -> None:
        """Call all observers; await any that return a coroutine (sync or async observers)."""
        try:
            for result in self._iter_results(ctx):
                if result is not None and asyncio.iscoroutine(result):
                    await result
        except Exception:
            raise  # Let observers propagate their errors


# Global registry
_registry = ObserverRegistry()


def observers(action: ObserverAction | str):
    """
    Decorator for global observers.
    Observers are called for any action matching the given type.

    Usage:
        @pgstorm.observers(action="fetch")
        def on_fetch(ctx):
            print(f"Fetching from {ctx.table}")
    """

    def decorator(func: ObserverCallback) -> ObserverCallback:
        _registry.register(action, func, table=None)
        return func

    return decorator


def table_observers(action: ObserverAction | str | None, table: type[Any]):
    """
    Decorator for table-specific observers.
    Registry filters by (action, table)—no model checking needed in your callback.

    If ``action`` is None, the observer is registered for **all** actions for
    the given table.

    Usage:
        @pgstorm.table_observers(action="post_save", table=User)
        def on_user_saved(ctx):
            print(f"Saved user: {ctx.extra.get('instance')}")

        # Called for any action on User
        @pgstorm.table_observers(action=None, table=User)
        def on_any_user_event(ctx):
            ...
    """

    def decorator(func: ObserverCallback) -> ObserverCallback:
        if action is None:
            # Register the same callback for all actions for this table
            for a in ALL_ACTIONS:
                _registry.register(a, func, table=table)
        else:
            _registry.register(action, func, table=table)
        return func

    return decorator


# Convenience wrappers for common global observer actions
def on_fetch(func: ObserverCallback) -> ObserverCallback:
    """Register a global fetch observer."""
    return observers(action=FETCH)(func)


def on_pre_save(func: ObserverCallback) -> ObserverCallback:
    """Register a global pre_save observer."""
    return observers(action=PRE_SAVE)(func)


def on_post_save(func: ObserverCallback) -> ObserverCallback:
    """Register a global post_save observer."""
    return observers(action=POST_SAVE)(func)


def on_pre_create(func: ObserverCallback) -> ObserverCallback:
    """Register a global pre_create observer."""
    return observers(action=PRE_CREATE)(func)


def on_post_create(func: ObserverCallback) -> ObserverCallback:
    """Register a global post_create observer."""
    return observers(action=POST_CREATE)(func)


def on_pre_bulk_create(func: ObserverCallback) -> ObserverCallback:
    """Register a global pre_bulk_create observer."""
    return observers(action=PRE_BULK_CREATE)(func)


def on_post_bulk_create(func: ObserverCallback) -> ObserverCallback:
    """Register a global post_bulk_create observer."""
    return observers(action=POST_BULK_CREATE)(func)


def on_pre_update(func: ObserverCallback) -> ObserverCallback:
    """Register a global pre_update observer."""
    return observers(action=PRE_UPDATE)(func)


def on_post_update(func: ObserverCallback) -> ObserverCallback:
    """Register a global post_update observer."""
    return observers(action=POST_UPDATE)(func)


def on_pre_bulk_update(func: ObserverCallback) -> ObserverCallback:
    """Register a global pre_bulk_update observer."""
    return observers(action=PRE_BULK_UPDATE)(func)


def on_post_bulk_update(func: ObserverCallback) -> ObserverCallback:
    """Register a global post_bulk_update observer."""
    return observers(action=POST_BULK_UPDATE)(func)


def on_pre_delete(func: ObserverCallback) -> ObserverCallback:
    """Register a global pre_delete observer."""
    return observers(action=PRE_DELETE)(func)


def on_post_delete(func: ObserverCallback) -> ObserverCallback:
    """Register a global post_delete observer."""
    return observers(action=POST_DELETE)(func)


def on_raw_sql(func: ObserverCallback) -> ObserverCallback:
    """Register a global raw_sql observer."""
    return observers(action=RAW_SQL)(func)


def on_connection_open(func: ObserverCallback) -> ObserverCallback:
    """Register a global connection_open observer."""
    return observers(action=CONNECTION_OPEN)(func)


def on_connection_close(func: ObserverCallback) -> ObserverCallback:
    """Register a global connection_close observer."""
    return observers(action=CONNECTION_CLOSE)(func)


def on_cursor_open(func: ObserverCallback) -> ObserverCallback:
    """Register a global cursor_open observer."""
    return observers(action=CURSOR_OPEN)(func)


def on_cursor_close(func: ObserverCallback) -> ObserverCallback:
    """Register a global cursor_close observer."""
    return observers(action=CURSOR_CLOSE)(func)


def on_query_before_execute(func: ObserverCallback) -> ObserverCallback:
    """Register a global query_before_execute observer."""
    return observers(action=QUERY_BEFORE_EXECUTE)(func)


def on_query_after_execute(func: ObserverCallback) -> ObserverCallback:
    """Register a global query_after_execute observer."""
    return observers(action=QUERY_AFTER_EXECUTE)(func)


def on_transaction_begin(func: ObserverCallback) -> ObserverCallback:
    """Register a global transaction_begin observer."""
    return observers(action=TRANSACTION_BEGIN)(func)


def on_transaction_commit(func: ObserverCallback) -> ObserverCallback:
    """Register a global transaction_commit observer."""
    return observers(action=TRANSACTION_COMMIT)(func)


def on_transaction_rollback(func: ObserverCallback) -> ObserverCallback:
    """Register a global transaction_rollback observer."""
    return observers(action=TRANSACTION_ROLLBACK)(func)


def notify(ctx: ObserverContext) -> None:
    """Notify all registered observers for the given context."""
    _registry.notify(ctx)


async def notify_async(ctx: ObserverContext) -> None:
    """Notify all registered observers; await any that return a coroutine (sync or async observers)."""
    await _registry.notify_async(ctx)


def get_registry() -> ObserverRegistry:
    """Return the global observer registry (for testing or advanced use)."""
    return _registry
