# Engine & Execution

## create_engine

Create an engine to connect to PostgreSQL:

```python
from pgstorm import create_engine

engine = create_engine("postgresql://user:pass@localhost/dbname")
```

By default, the engine is set in a context variable so all querysets use it automatically.

### Parameters

- **conninfo** — PostgreSQL connection string
- **interface** — Driver to use (default: `"psycopg3"`)
- **set_global** — If `True` (default), set engine in context for querysets
- **\*\*kwargs** — Passed to the underlying connection (e.g. `connect_timeout`)

### Interfaces

| Interface | Sync/Async | Notes |
|-----------|------------|-------|
| `psycopg2` | Sync | Legacy driver |
| `psycopg3` / `psycopg3_sync` | Sync | psycopg v3 |
| `psycopg3_async` | Async | psycopg v3 async |
| `asyncpg` | Async | asyncpg driver |

```python
# Sync
engine = create_engine("postgresql://...", interface="psycopg3")

# Async
engine = create_engine("postgresql://...", interface="psycopg3_async")
# or
engine = create_engine("postgresql://...", interface="asyncpg")
```

## Fetching Results

### Sync

```python
users = list(User.objects.filter(User.age > 18))
user = User.objects.filter(User.id == 1)[0]
for u in User.objects.all():
    print(u.email)
```

### Async

```python
users = await User.objects.filter(User.age > 18).fetch()
```

## Transactions

### Sync

```python
import pgstorm

with pgstorm.transaction():
    # all queries in this block run in a transaction
    User.objects.filter(User.id == 1)  # uses same connection
    # commit on success, rollback on exception
```

### Async

```python
import pgstorm

async with pgstorm.transaction():
    await User.objects.all().fetch()
```

## set_search_path

Set the PostgreSQL `search_path` inside a transaction. Must be called within `pgstorm.transaction()`.

```python
import pgstorm

with pgstorm.transaction():
    pgstorm.set_search_path("my_schema", "public")  # transaction-scoped (SET LOCAL)
    # or
    pgstorm.set_search_path("my_schema", session=True)  # session-scoped (SET)
```

## Manual Control

```python
engine.begin()
# ... run queries ...
engine.commit()
# or on error:
engine.rollback()
```

For async, use `await engine.begin()`, `await engine.commit()`, `await engine.rollback()`.

## Context Variable

The engine is stored in a `ContextVar`. You can set it manually:

```python
from pgstorm.engine import engine, create_engine

eng = create_engine("postgresql://...", set_global=False)
engine.set(eng)
# querysets now use eng
```

This is useful for multi-tenant or request-scoped engines.
