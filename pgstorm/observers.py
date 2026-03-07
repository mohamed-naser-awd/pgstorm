"""
Observer pattern for pgstorm ORM hooks.

Register observers for various database operations:

  @pgstorm.observers(action="fetch")
  def on_fetch(ctx):
      print(f"Fetched from {ctx.table}")

  @pgstorm.table_observers(action="create", table=User)
  def on_user_create(ctx):
      print(f"Created user: {ctx.extra.get('instance')}")

Actions: fetch, create, bulk_create, update, bulk_update, save, delete,
         raw_sql, connection_open, connection_close, cursor_open, cursor_close,
         query_before_execute, query_after_execute,
         transaction_begin, transaction_commit, transaction_rollback
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Type

# Type for observer callback - use this to type your observer functions
ObserverCallback = Callable[["ObserverContext"], None]

# Valid observer actions (for type hints)
ObserverAction = Literal[
    "fetch",
    "create",
    "bulk_create",
    "update",
    "bulk_update",
    "save",
    "delete",
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

# Action constants for observers
FETCH = "fetch"
CREATE = "create"
BULK_CREATE = "bulk_create"
UPDATE = "update"
BULK_UPDATE = "bulk_update"
SAVE = "save"  # instance save (create or update)
DELETE = "delete"
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

# All actions that can be observed
ALL_ACTIONS = frozenset({
    FETCH,
    CREATE,
    BULK_CREATE,
    UPDATE,
    BULK_UPDATE,
    SAVE,
    DELETE,
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


class ObserverRegistry:
    """Registry for global and table-specific observers."""

    def __init__(self) -> None:
        self._observers: list[_ObserverEntry] = []

    def register(
        self,
        action: str,
        callback: ObserverCallback,
        table: type[Any] | None = None,
    ) -> None:
        if action not in ALL_ACTIONS:
            raise ValueError(
                f"Unknown action {action!r}. Valid actions: {sorted(ALL_ACTIONS)}"
            )
        self._observers.append(_ObserverEntry(action=action, callback=callback, table=table))

    def notify(self, ctx: ObserverContext) -> None:
        """Call all observers matching the context's action and table."""
        for entry in self._observers:
            if entry.action != ctx.action:
                continue
            if entry.table is not None:
                if ctx.model is None or not issubclass(ctx.model, entry.table):
                    continue
            try:
                entry.callback(ctx)
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


def table_observers(action: ObserverAction | str, table: type[Any]):
    """
    Decorator for table-specific observers.
    Observers are only called when the action matches and the table/model matches.

    Usage:
        @pgstorm.table_observers(action="create", table=User)
        def on_user_create(ctx):
            print(f"Created user: {ctx.extra.get('instance')}")
    """

    def decorator(func: ObserverCallback) -> ObserverCallback:
        _registry.register(action, func, table=table)
        return func

    return decorator


def notify(ctx: ObserverContext) -> None:
    """Notify all registered observers for the given context."""
    _registry.notify(ctx)


def get_registry() -> ObserverRegistry:
    """Return the global observer registry (for testing or advanced use)."""
    return _registry
