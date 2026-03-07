"""
Example: Using pgstorm observers for database operation hooks.

Run with: python -m example.observers_example
(Requires database connection)
"""

from pgstorm import ObserverContext, observers, table_observers
from pgstorm.observers import (
    FETCH,
    CREATE,
    BULK_CREATE,
    UPDATE,
    BULK_UPDATE,
    DELETE,
    RAW_SQL,
    CONNECTION_OPEN,
    CURSOR_OPEN,
    CURSOR_CLOSE,
    QUERY_BEFORE_EXECUTE,
    QUERY_AFTER_EXECUTE,
    TRANSACTION_BEGIN,
    TRANSACTION_COMMIT,
    TRANSACTION_ROLLBACK,
)
from example.model import User


# Global observer - called for any fetch
@observers(action=FETCH)
def on_any_fetch(ctx: ObserverContext) -> None:
    print(f"[fetch] table={ctx.table}, model={ctx.model}")


# Table-specific observer - only for User creates
@table_observers(action=CREATE, table=User)
def on_user_create(ctx: ObserverContext) -> None:
    instance = ctx.extra.get("instance")
    print(f"[create] User: {instance}")


# Global observer for all queries (before execution)
@observers(action=QUERY_BEFORE_EXECUTE)
def before_query(ctx: ObserverContext) -> None:
    action = ctx.extra.get("query_action", "?")
    print(f"[before] action={action}, table={ctx.table}")


# Global observer for all queries (after execution)
@observers(action=QUERY_AFTER_EXECUTE)
def after_query(ctx: ObserverContext) -> None:
    rows = ctx.result if isinstance(ctx.result, list) else []
    print(f"[after] rows={len(rows)}")


# Connection/cursor hooks
@observers(action=CONNECTION_OPEN)
def on_connection_open(ctx: ObserverContext) -> None:
    print("[connection_open]")


@observers(action=CURSOR_OPEN)
def on_cursor_open(ctx: ObserverContext) -> None:
    print("[cursor_open]")


@observers(action=CURSOR_CLOSE)
def on_cursor_close(ctx: ObserverContext) -> None:
    print("[cursor_close]")


# Transaction hooks
@observers(action=TRANSACTION_BEGIN)
def on_transaction_begin(ctx: ObserverContext) -> None:
    print("[transaction_begin]")


@observers(action=TRANSACTION_COMMIT)
def on_transaction_commit(ctx: ObserverContext) -> None:
    print("[transaction_commit]")


if __name__ == "__main__":
    from pgstorm.engine import create_engine

    create_engine("postgresql://localhost/pgstorm_test")
    from example.model import User

    # These will trigger the observers
    list(User.objects.all())  # fetch
    # User.objects.create(email="test@example.com")  # create
