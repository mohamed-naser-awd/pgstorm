# Observers & hooks

pgstorm provides an observer system for registering callbacks around database operations. Observers are useful for logging, auditing, metrics, and cross‑cutting concerns that should react to queries, connections, cursors, or transactions.

Observers live in `pgstorm.observers` and are automatically invoked by the engine and QuerySet layer; you normally only need to register decorators, not call the observer machinery directly.

## Concepts

### ObserverContext

Each observer receives an `ObserverContext` instance describing the current event:

```python
from pgstorm.observers import ObserverContext

class ObserverContext:
    action: str                  # e.g. "fetch", "pre_create", "post_update"
    model: type[Any] | None      # Model class, if applicable
    table: str | None            # Table name, if applicable
    compiled: Any                # CompiledQuery or None
    params: list[Any]            # Ordered parameters
    result: Any                  # Query result (set for "query_after_execute")
    extra: dict[str, Any]        # Extra metadata (e.g. "query_action", "instance")
```

You typically read `ctx.action`, `ctx.table`, `ctx.model`, and `ctx.extra` to understand what happened.

### Global vs table‑specific observers

- **Global observers** run for *all* tables for a given action (e.g. every fetch).
- **Table‑specific observers** only run for a specific model/table and action.

Both are wired through the same global registry and use the same `ObserverContext` type.

## Registering observers

Import helpers from `pgstorm.observers`:

```python
from pgstorm.observers import (
    ObserverContext,
    observers,
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
```

### Global observers

Use `on_*` helpers (or the generic `observers()` decorator) for global observers:

```python
@on_fetch
def fetch_observer(ctx: ObserverContext) -> None:
    # Called for any SELECT
    print(f"[fetch] table={ctx.table}, model={ctx.model}")


@on_query_before_execute
def query_before_execute_observer(ctx: ObserverContext) -> None:
    # Runs before any query is executed
    action = ctx.extra.get("query_action", "?")
    print(f"[before] action={action}, table={ctx.table}")


@on_query_after_execute
def query_after_execute_observer(ctx: ObserverContext) -> None:
    # Runs after any query is executed
    rows = ctx.result if isinstance(ctx.result, list) else []
    print(f"[after] rows={len(rows)}")
```

### Table‑specific observers

Use `table_observers(action=..., table=Model)` to restrict callbacks to a single model:

```python
@table_observers(action=POST_CREATE, table=User)
def user_create_observer(ctx: ObserverContext) -> None:
    # Only called for User INSERTs
    instance = ctx.extra.get("instance")
    print(f"[post_create] User: {instance}")
```

If you pass `action=None`, the observer will be registered for **all** actions for that table:

```python
@table_observers(action=None, table=User)
def any_user_event(ctx: ObserverContext) -> None:
    print(f"[{ctx.action}] User event on table={ctx.table}")
```

## Actions

Actions are string constants defined in `pgstorm.observers` and used to classify events. Common groups:

- **Query lifecycle**
  - `"fetch"`
  - `"pre_create"`, `"post_create"`
  - `"pre_update"`, `"post_update"`
  - `"pre_delete"`, `"post_delete"`
- **Bulk writes**
  - `"pre_bulk_create"`, `"post_bulk_create"`
  - `"pre_bulk_update"`, `"post_bulk_update"`
- **Connections and cursors**
  - `"connection_open"`, `"connection_close"`
  - `"cursor_open"`, `"cursor_close"`
- **Execution and transactions**
  - `"query_before_execute"`, `"query_after_execute"`
  - `"transaction_begin"`, `"transaction_commit"`, `"transaction_rollback"`

You can import named constants (e.g. `POST_CREATE`, `QUERY_BEFORE_EXECUTE`) from `pgstorm.observers` for type‑safe usage.

## Sync vs async observers

Observers can be **sync** or **async**:

- With a **sync engine**, use normal (sync) observer functions. If you accidentally return a coroutine from a sync observer, pgstorm will raise a `RuntimeError`.
- With an **async engine**, observers can be sync or async; async observers are awaited automatically.

In both cases, exceptions raised by observers are propagated, so you can fail fast on unexpected situations.

## End‑to‑end example

The `example/observers_example.py` module shows a complete setup:

```python
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


@on_fetch
def fetch_observer(ctx: ObserverContext) -> None:
    print(f"[fetch] table={ctx.table}, model={ctx.model}")


@table_observers(action=POST_CREATE, table=User)
def user_create_observer(ctx: ObserverContext) -> None:
    instance = ctx.extra.get("instance")
    print(f"[post_create] User: {instance}")


@on_query_before_execute
def query_before_execute_observer(ctx: ObserverContext) -> None:
    action = ctx.extra.get("query_action", "?")
    print(f"[before] action={action}, table={ctx.table}")


@on_query_after_execute
def query_after_execute_observer(ctx: ObserverContext) -> None:
    rows = ctx.result if isinstance(ctx.result, list) else []
    print(f"[after] rows={len(rows)}")


@on_connection_open
def connection_open_observer(ctx: ObserverContext) -> None:
    print("[connection_open]")


@on_cursor_open
def cursor_open_observer(ctx: ObserverContext) -> None:
    print("[cursor_open]")


@on_cursor_close
def cursor_close_observer(ctx: ObserverContext) -> None:
    print("[cursor_close]")


@on_transaction_begin
def transaction_begin_observer(ctx: ObserverContext) -> None:
    print("[transaction_begin]")


@on_transaction_commit
def transaction_commit_observer(ctx: ObserverContext) -> None:
    print("[transaction_commit]")
```

Run the example with:

```bash
python -m example.observers_example
```

Make sure you have a PostgreSQL database configured (see the main `README` and `example/model.py` for connection details).

