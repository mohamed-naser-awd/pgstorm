# Installation & Setup

## Requirements

- Python 3.10+
- PostgreSQL database
- A driver matching your chosen interface (installed automatically via extras)

## Install

```bash
# Default: psycopg3 with binary (sync and async)
pip install pgstorm

# Or install with a specific driver
# psycopg2: normal (requires libpq) or binary (pre-built)
pip install pgstorm[psycopg2]        # psycopg2 (sync)
pip install pgstorm[psycopg2-binary] # psycopg2-binary (sync)

# psycopg3: normal or binary
pip install pgstorm[psycopg3]        # psycopg3 (normal build)
pip install pgstorm[psycopg3-binary] # psycopg3 binary (pre-built)

pip install pgstorm[asyncpg]         # asyncpg (async)
pip install pgstorm[all]             # all drivers (binary variants)
```

**From source** (development):

```bash
pip install -e .
pip install -e ".[asyncpg]"     # with asyncpg
```

## Minimal Setup

```python
from pgstorm import BaseModel, types, create_engine

# 1. Define models
class User(BaseModel):
    __table__ = "users"
    id: types.Integer
    email: types.String

# 2. Create engine (connects to DB and sets global context)
engine = create_engine("postgresql://user:password@localhost:5432/mydb")

# 3. Use querysets
users = list(User.objects.all())
```

## Connection String

Use a standard PostgreSQL connection string:

```
postgresql://user:password@host:port/database
postgresql://user@localhost/dbname
postgresql:///dbname  # localhost, current user
```

## Without Global Engine

If you prefer not to use the global context, create an engine with `set_global=False` and pass it explicitly, or use `engine.set()` in a context:

```python
from pgstorm import create_engine, engine

eng = create_engine("postgresql://...", set_global=False)
# Manually set for this context
engine.set(eng)
# ... use querysets ...
```
