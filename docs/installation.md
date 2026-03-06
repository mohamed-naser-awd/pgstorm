# Installation & Setup

## Requirements

- Python 3.10+
- PostgreSQL database
- [psycopg](https://www.psycopg.org/psycopg3/) (for psycopg3 interfaces) or psycopg2 / asyncpg depending on your chosen interface

## Install

```bash
pip install psycopg[binary]
```

Then add the `pgstorm` package to your project. If you have a `pyproject.toml`:

```bash
pip install -e .
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
