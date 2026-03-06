# pgstorm

A lightweight PostgreSQL query builder and mini-ORM for Python. Compose type-safe queries that compile to parameterized SQL, then execute them using a pluggable engine (sync or async).

## Features

- **Type-safe models** — Define models with type annotations; `__table__` or `__tablename__` for table names
- **Rich QuerySet API** — `filter`, `exclude`, `order_by`, `limit`, `offset`, `join`, `aggregate`, `annotate`, `alias`
- **Q objects** — Combine conditions with `|` (OR), `&` (AND), `~` (NOT)
- **Subqueries** — `Subquery` and `OuterRef` for correlated subqueries
- **F expressions** — Reference annotations/aliases in filters and `order_by`
- **SQL functions** — `Concat`, `Coalesce`, `Upper`, `Lower`, `Now`, `DateTrunc`, `Func_`, and more
- **Aggregates** — `Min`, `Max`, `Count`, `Sum`, `Avg`
- **Writes included** — `create`, `bulk_create`, `update`, `delete` (sync or `await` with async engines)
- **Engine abstraction** — Sync (psycopg2, psycopg3) and async (psycopg3_async, asyncpg) interfaces
- **Transactions** — `with engine.transaction():` or `async with engine.transaction():`
- **Schema support** — `using_schema()` and per-join `rhs_schema`

## Requirements

- Python **3.10+**
- A PostgreSQL database
- A driver matching your chosen interface:
  - **psycopg3**: `psycopg[binary]` (recommended)
  - **psycopg2**: `psycopg2-binary`
  - **asyncpg**: `asyncpg`

## Installation (from source)

This repository currently doesn’t ship packaging metadata (`pyproject.toml` / `setup.py`). The simplest way to try it is:

1. Install a driver dependency (see below).
2. Run your code from the repository root (so `import pgstorm` resolves), or add the repo root to `PYTHONPATH`.

```bash
pip install psycopg[binary]
```

Optional (asyncpg):

```bash
pip install asyncpg
```

## Quick Start

```python
from pgstorm import BaseModel, types, create_engine

class User(BaseModel):
    __table__ = "users"
    id: types.Integer[types.IS_PRIMARY_KEY_FIELD]
    age: types.Integer
    email: types.String

class UserProfile(BaseModel):
    __table__ = "user_profile"
    user: types.ForeignKey[User, types.ON_DELETE_CASCADE]

# Create engine (sets global context for querysets)
engine = create_engine("postgresql://user:pass@localhost/dbname", interface="psycopg3")

# Build and compile a query
qs = UserProfile.objects.filter(
    UserProfile.user.email.like("%@example.com")
).join(User, UserProfile.user.id == User.id)

compiled = qs.compiled()
print(compiled.sql.as_string(None))
print(compiled.params)

# Execute and iterate (uses engine from context)
for profile in qs:
    print(profile.user.email)
```

## Async example (asyncpg)

`QuerySet.fetch()` and other methods return an awaitable when the configured engine is async.

```python
import asyncio
from pgstorm import create_engine, Subquery
from example.model import User, AuditLog

db_credentials = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "admin",
    "dbname": "testdb",
}

async def main():
    create_engine(db_credentials, interface="asyncpg")

    log = await AuditLog.objects.create(
        user=Subquery(
            User.objects.using_schema("tenant1")
                .filter(User.email == "mohamed@example.com")
                .columns("id")
        ),
        action="INSERT",
        target_table="user",
        target_id=2,
    )
    print("log id:", log.id)

    rows = await User.objects.using_schema("tenant1").filter(User.email.like("%@example.com")).fetch()
    for user in rows:
        print(user.email)

    print("count:", await User.objects.count())

asyncio.run(main())
```

## Models

Define models by subclassing `BaseModel` and annotating attributes with `types`:

```python
from pgstorm import BaseModel, types

class Product(BaseModel):
    __table__ = "products"
    id: types.Integer[types.IS_PRIMARY_KEY_FIELD]
    name: types.String
    price: types.Integer
```

Use `__table__` or `__tablename__` to set the table name; otherwise the class name (lowercased) is used.

### Types

- **Scalars**: `types.Integer`, `types.String`, `types.BigSerial`, `types.Jsonb`, `types.Inet`, `types.Varchar(20)`, `types.TimestampTZ(default=...)`
- **Relations**: `types.ForeignKey[User]`, `types.OneToOne`, `types.ManyToMany`
- **Relation metadata**: `types.ON_DELETE_CASCADE`, `types.FK_FIELD("email")`, `types.FK_COLUMN("user_email")`, `types.ReverseName("profiles")`

```python
user: types.ForeignKey[User, types.ON_DELETE_CASCADE, types.FK_FIELD("email")]
```

If you want your editor/type checker to understand that `profile.user` is a `User`, use `Annotated`:

```python
from pgstorm.types import Annotated

user: Annotated[User, types.ForeignKey[User, types.ON_DELETE_CASCADE]]
```

## Engine & Execution

Create an engine with `create_engine()`. By default it sets the engine in a context variable so querysets use it automatically.

```python
from pgstorm import create_engine

# Sync (default)
engine = create_engine("postgresql://user:pass@localhost/db", interface="psycopg3")

# Async
engine = create_engine("postgresql://...", interface="psycopg3_async")
# or
engine = create_engine("postgresql://...", interface="asyncpg")
```

**Interfaces**: `psycopg2`, `psycopg3`, `psycopg3_sync`, `psycopg3_async`, `asyncpg`

### Fetching results

```python
# Sync: iterate or index
users = list(User.objects.filter(User.age > 18))
user = User.objects.filter(User.id == 1)[0]

# Async: use await fetch()
users = await User.objects.filter(User.age > 18).fetch()
```

### Transactions

```python
# Sync
with engine.transaction():
    # queries run in transaction
    pass

# Async
async with engine.transaction():
    await User.objects.all().fetch()
```

## QuerySet API

### Filtering

```python
# Simple comparisons (==, !=, <, <=, >, >=)
User.objects.filter(User.age >= 18)
User.objects.filter(User.email == "a@b.com")

# LIKE / ILIKE
User.objects.filter(User.email.like("%@example.com"))
User.objects.filter(User.name.ilike("%john%"))

# IN
User.objects.filter(User.id.in_([1, 2, 3]))
User.objects.filter(User.id.in_(Subquery(Order.objects.columns("user_id"))))

# Exclude
User.objects.filter(User.age > 18).exclude(User.deleted)
```

### Q objects (AND / OR / NOT)

```python
from pgstorm import Q, and_, or_, not_

User.objects.filter(Q(User.age > 18) | Q(User.age < 5))
User.objects.filter(and_(Q(User.active), Q(User.verified)))
User.objects.filter(~Q(User.deleted))
```

### Joins

```python
UserProfile.objects.join(
    User,
    UserProfile.user.email == User.email,
    join_type="LEFT"
)
```

### Schemas

```python
User.objects.using_schema("tenant_1").filter(...)
UserProfile.objects.join(User, ..., rhs_schema="tenant_2")
```

### Aggregates

```python
from pgstorm import Min, Max, Count, Sum, Avg

# Positional: alias = col_name_function_name (e.g. price_min)
Product.objects.aggregate(Min(Product.price), Max(Product.price))

# Keyword: alias = key
Product.objects.aggregate(total=Sum(Product.price), cnt=Count())

# COUNT(*)
Product.objects.aggregate(row_count=Count())
```

### Annotate & Alias

```python
from pgstorm import Concat, F

# annotate: add computed columns to SELECT; results include them
User.objects.annotate(full_name=Concat(User.first_name, " ", User.last_name))

# alias: define expressions for filter/order_by without including in SELECT
User.objects.alias(full_name=Concat(User.first_name, " ", User.last_name)).filter(
    F("full_name").ilike("%mohamed%")
)
```

### Subqueries & OuterRef

```python
from pgstorm import Subquery, OuterRef

# Users who have at least one order
User.objects.filter(
    User.id.in_(
        Subquery(
            Order.objects.filter(Order.user_id == OuterRef(User.id)).columns("user_id")
        )
    )
)
```

### Other

- `order_by(User.age)` — ORDER BY
- `limit(10)`, `offset(20)` — LIMIT / OFFSET
- `distinct()` — SELECT DISTINCT
- `defer("col")`, `columns("col1", "col2")` — column selection
- `as_cte(name)` — use queryset as CTE

## Compiling to SQL

```python
qs = User.objects.filter(User.age > 18).limit(10)
compiled = qs.compiled()

# For psycopg
sql, params = qs.as_sql()
cursor.execute(sql, params)
```

## SQL Functions

Built-in: `Concat`, `Coalesce`, `Upper`, `Lower`, `Length`, `Trim`, `Replace`, `NullIf`, `Abs`, `Round`, `Floor`, `Ceil`, `Now`, `CurrentDate`, `CurrentTimestamp`, `DateTrunc`. Use `Func_("name", arg1, arg2)` for any other PostgreSQL function.

## Documentation

See the [docs/](docs/) folder for detailed documentation:

- [Installation & Setup](docs/installation.md)
- [Models & Types](docs/models.md)
- [QuerySet API](docs/queryset.md)
- [Engine & Execution](docs/engine.md)
- [Functions & Aggregates](docs/functions.md)
- [Subqueries](docs/subqueries.md)
- [API Reference](docs/api-reference.md)

## License

Not specified yet (README previously said MIT, but a `LICENSE` file is not currently present in this repository).
