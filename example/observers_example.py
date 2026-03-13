"""
Example: Using pgstorm observers for database operation hooks.

Run with: python -m example.observers_example
(Requires database connection)
"""

from pgstorm.observers import (
    ObserverContext,
    table_observers,
    on_fetch,
    on_query_before_execute,
    on_query_after_execute,
    on_connection_open,
    on_cursor_open,
    on_cursor_close,
    on_transaction_begin,
    on_transaction_commit,
    POST_CREATE,
)
from example.model import User


# Global observer - called for any fetch
@on_fetch
def fetch_observer(ctx: ObserverContext) -> None:
    print(f"[fetch] table={ctx.table}, model={ctx.model}")


# Table-specific observer - only for User creates (no model check needed)
@table_observers(action=POST_CREATE, table=User)
def user_create_observer(ctx: ObserverContext) -> None:
    instance = ctx.extra.get("instance")
    print(f"[post_create] User: {instance}")


# Global observer for all queries (before execution)
@on_query_before_execute
def query_before_execute_observer(ctx: ObserverContext) -> None:
    action = ctx.extra.get("query_action", "?")
    print(f"[before] action={action}, table={ctx.table}")


# Global observer for all queries (after execution)
@on_query_after_execute
def query_after_execute_observer(ctx: ObserverContext) -> None:
    rows = ctx.result if isinstance(ctx.result, list) else []
    print(f"[after] rows={len(rows)}")


# Connection/cursor hooks
@on_connection_open
def connection_open_observer(ctx: ObserverContext) -> None:
    print("[connection_open]")


@on_cursor_open
def cursor_open_observer(ctx: ObserverContext) -> None:
    print("[cursor_open]")


@on_cursor_close
def cursor_close_observer(ctx: ObserverContext) -> None:
    print("[cursor_close]")


# Transaction hooks
@on_transaction_begin
def transaction_begin_observer(ctx: ObserverContext) -> None:
    print("[transaction_begin]")


@on_transaction_commit
def transaction_commit_observer(ctx: ObserverContext) -> None:
    print("[transaction_commit]")


if __name__ == "__main__":
    from pgstorm.engine import create_engine

    create_engine("postgresql://localhost/pgstorm_test")
    from example.model import User

    # These will trigger the observers
    list(User.objects.all())  # fetch
    # User.objects.create(email="test@example.com")  # create
