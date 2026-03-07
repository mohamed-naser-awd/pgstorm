# API Reference

Structured reference for pgstorm's public API. All items are importable from `pgstorm` unless noted.

---

## Engine & Context

### `create_engine`

```python
def create_engine(
    conninfo: str | dict[str, Any],
    interface: str | Type[EngineInterface] = "psycopg3",
    *,
    set_global: bool = True,
    **kwargs: Any,
) -> BaseEngine
```

Create a database engine and optionally set it in the global context.

| Parameter | Type | Description |
|-----------|------|-------------|
| `conninfo` | `str` or `dict` | PostgreSQL connection string (e.g. `"postgresql://user:pass@localhost/db"`) or dict (`{"host": "...", "port": 5432, "user": "...", "password": "...", "dbname": "..."}`) |
| `interface` | `str` | One of `"psycopg2"`, `"psycopg3"`, `"psycopg3_sync"`, `"psycopg3_async"`, `"asyncpg"` |
| `set_global` | `bool` | If `True` (default), set engine in context so querysets use it automatically |
| `**kwargs` | | Passed to the interface constructor (e.g. `connect_timeout`) |

**Returns:** `SyncEngine` or `AsyncEngine` depending on the interface.

---

### `engine`

```python
engine: ContextVar[BaseEngine | None]
```

Context variable holding the current engine. Set by `create_engine()` when `set_global=True`. Use `engine.set(eng)` for manual control.

---

### `transaction()`

```python
# Sync
with pgstorm.transaction():
    ...

# Async
async with pgstorm.transaction():
    ...
```

Context manager for transactions using the engine from context. Commits on success, rolls back on exception.

---

### `set_search_path`

```python
# Transaction-scoped (SET LOCAL) - default
with pgstorm.transaction():
    pgstorm.set_search_path("my_schema", "public")
    # queries use my_schema, public

# Session-scoped (SET) - persists until connection closes
with pgstorm.transaction():
    pgstorm.set_search_path("my_schema", session=True)
```

Set the PostgreSQL `search_path`. **Must be called inside** `pgstorm.transaction()` — raises `RuntimeError` otherwise.

| Parameter | Type | Description |
|-----------|------|-------------|
| `*schemas` | `str` | Schema names (e.g. `"my_schema"`, `"public"`) |
| `session` | `bool` | If `False` (default), use `SET LOCAL` (transaction-scoped). If `True`, use `SET` (session-scoped) |

---

## BaseModel

Base class for all pgstorm models. Define models by subclassing and annotating attributes with `types`.

### Class attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `objects` | `QuerySet[Self]` | Manager for querying. Access via `Model.objects` |

### Instance methods

#### `__init__(**kwargs)`

Accept keyword args for model fields. Used by `Model.objects.create(**kwargs)` and manual instantiation.

---

#### `create(*, schema=None) -> Self | Awaitable[Self]`

Insert this instance. With sync engine returns `Self`; with async returns `Awaitable[Self]` — use `await`. If primary key is `None` it is omitted. Uses `RETURNING *` and updates the instance with returned values.

| Parameter | Type | Description |
|-----------|------|-------------|
| `schema` | `str \| None` | Database schema (e.g. `"tenant1"`) |

---

#### `update(*, schema=None) -> Self | Awaitable[Self]`

Update this instance by primary key. Instance must have a non-`None` primary key. Uses `RETURNING *` and updates the instance.

---

#### `refresh_from_db(*, schema=None) -> Self | Awaitable[Self]`

Reload this instance from the database. Instance must have a non-`None` primary key. Raises `RuntimeError` if the record no longer exists.

---

#### `delete(*, schema=None) -> None | Awaitable[None]`

Delete this instance by primary key. Instance must have a non-`None` primary key.

---

## QuerySet

Returned by `Model.objects`. QuerySets are lazy — they execute when you iterate, index, call `fetch()`, or use write methods.

### Filtering & selection

#### `filter(*args) -> Self`

Add filter conditions. Accepts `Expression`, `NotExpression`, or `Q` objects.

```python
User.objects.filter(User.age >= 18)
User.objects.filter(Q(User.age > 18) | Q(User.age < 5))
```

---

#### `exclude(*args) -> Self`

Add negated filter conditions (equivalent to `filter(~expr)`).

---

#### `order_by(*args) -> Self`

Add `ORDER BY` clauses. Accepts column refs or expressions.

```python
User.objects.order_by(User.age)
User.objects.order_by(F("full_name"))
```

---

#### `limit(limit: int) -> Self`

Set `LIMIT`.

---

#### `offset(offset: int) -> Self`

Set `OFFSET`.

---

#### `distinct(*args: str) -> Self`

Add `SELECT DISTINCT`.

---

#### `columns(*args: str) -> Self`

Restrict `SELECT` to the given column names (attribute names).

---

#### `defer(*args: str) -> Self`

Exclude columns from `SELECT`.

---

#### `using_schema(schema: str | None) -> Self`

Set the database schema for the main table and default for joins.

---

### Joins

#### `join(join_with, on, join_type="LEFT", rhs_schema=None) -> Self`

| Parameter | Type | Description |
|-----------|------|-------------|
| `join_with` | `type[BaseModel]` | Model class to join |
| `on` | `Expression` | Join condition (e.g. `UserProfile.user.id == User.id`) |
| `join_type` | `str` | `"LEFT"`, `"RIGHT"`, `"INNER"`, `"FULL"`, or `"LATERAL"` |
| `rhs_schema` | `str \| None` | Schema for the joined table |

---

### Aggregates & annotations

#### `aggregate(*args, having=..., **kwargs) -> dict | list[dict] | Awaitable`

Execute aggregate functions and return results immediately. Without `group_by`: returns a single dict. With `group_by`: returns a list of dicts. Use `having=` to filter on aggregate results.

```python
Product.objects.aggregate(Min(Product.price), total=Sum(Product.price), cnt=Count())
# -> {"price_min": 10, "total": 100, "cnt": 5}
Product.objects.group_by(Product.category).aggregate(total=Sum(Product.price))
# -> [{"category": "A", "total": 100}, {"category": "B", "total": 200}]
```

---

#### `annotate(**kwargs) -> Self`

Add computed expressions to `SELECT`. Results include these values.

```python
User.objects.annotate(full_name=Concat(User.first_name, " ", User.last_name))
```

---

#### `alias(**kwargs) -> Self`

Define expressions for use in `filter` or `order_by` without including them in `SELECT`. Reference via `F("alias_name")`.

```python
User.objects.alias(full_name=Concat(...)).filter(F("full_name").ilike("%x%"))
```

---

### Fetching & iteration

#### `fetch() -> list[T] | Awaitable[list[T]]`

Load results. With sync engine returns `list[T]`. With async engine returns `Awaitable[list[T]]` — use `await`.

---

#### `get(*filters) -> T`

Filter, limit to 1, and return the first row. Raises `IndexError` if empty.

---

#### `__iter__` / `__len__` / `__getitem__`

Iteration, `len(qs)`, and `qs[i]` trigger evaluation (sync engine only). For async, use `await qs.fetch()` then iterate.

---

### Writes

#### `create(**kwargs) -> T | Awaitable[T]`

Create and insert a single record. With async engine use `await`.

```python
user = await User.objects.create(email="a@b.com", age=25)
```

---

#### `bulk_create(objs, *, returning=True, batch_size=None) -> list[T] | Awaitable[list[T]]`

Insert multiple instances. If `returning=True` (default), populates generated primary keys on each instance. If `batch_size` is set, inserts are split into batches of that size; default `None` inserts all at once.

---

#### `bulk_update(objs, fields) -> None | Awaitable[None]`

Update multiple instances. `fields` is a list of attribute names to update. Each object must have a non-`None` primary key.

---

#### `update(**kwargs) -> None | Awaitable[None]`

Update all rows matching the queryset's filters.

```python
await User.objects.filter(User.age < 18).update(active=False)
```

---

#### `delete() -> None | Awaitable[None]`

Delete all rows matching the queryset's filters.

---

### Count & compilation

#### `count() -> int | Awaitable[int]`

Return the number of rows matching this queryset. With async engine use `await`.

---

#### `compiled() -> CompiledQuery`

Compile to a `CompiledQuery` (`.sql`, `.params`) without executing. Useful for debugging.

---

#### `as_sql() -> tuple[Composable, list]`

Return `(sql, params)` suitable for `cursor.execute(sql, params)`.

---

#### `as_cte(name=None) -> Self`

Mark this queryset as a CTE with the given name.

---

#### `all() -> Self`

No-op; returns self. Use for `Model.objects.all()`.

---

## Types (`pgstorm.types`)

Import as `from pgstorm import types` or `from pgstorm.types import ...`.

### Scalar types

| Type | PostgreSQL | Python |
|------|------------|--------|
| `types.Integer` | INTEGER | `int` |
| `types.String` | TEXT | `str` |
| `types.BigInt` | BIGINT | `int` |
| `types.BigSerial` | BIGSERIAL | `int` |
| `types.Jsonb` | JSONB | `dict` / `list` |
| `types.Inet` | INET | `str` |
| `types.Varchar(length)` | VARCHAR(n) | `str` |
| `types.TimestampTZ(default=..., precision=...)` | TIMESTAMP WITH TIME ZONE | `datetime` |

### Primary key

Use `types.Integer[types.IS_PRIMARY_KEY_FIELD]` or `types.BigSerial[types.IS_PRIMARY_KEY_FIELD]` for primary key fields.

### Relation types

| Type | Description |
|------|-------------|
| `types.ForeignKey[User]` | Many-to-one |
| `types.OneToOne[User]` | One-to-one |
| `types.ManyToMany[Tag]` | Many-to-many |

### Relation metadata (use inside brackets)

| Metadata | Description |
|----------|-------------|
| `types.ON_DELETE_CASCADE` | ON DELETE CASCADE |
| `types.ON_DELETE_RESTRICT` | ON DELETE RESTRICT |
| `types.ON_DELETE_SET_NULL` | ON DELETE SET NULL |
| `types.ON_DELETE_NO_ACTION` | ON DELETE NO ACTION |
| `types.FK_FIELD("email")` | Reference target's `email` instead of primary key |
| `types.FK_COLUMN("user_email")` | Use `user_email` as DB column name (default: `{attr}_id`) |
| `types.ReverseName("profiles")` | Reverse relation name on target model |

### Type checker support

For editor/type checker support on instance access (`profile.user` → `User`), use `Annotated`:

```python
from typing import Annotated
user: Annotated[User, types.ForeignKey[User, types.ON_DELETE_CASCADE]]
```

---

## Q, F, Subquery, OuterRef

### `Q(expression)`

Wraps filter expressions. Supports `|` (OR), `&` (AND), `~` (NOT).

```python
Q(User.age > 18) | Q(User.age < 5)
Q(User.active) & Q(User.verified)
~Q(User.deleted)
```

---

### `and_(*conditions) -> Q`

Combine conditions with AND.

---

### `or_(*conditions) -> Q`

Combine conditions with OR.

---

### `not_(condition) -> Q`

Negate a condition.

---

### `F(name)`

Reference an annotation or alias by name. Use in `filter` or `order_by` when the expression was defined via `alias()`.

```python
User.objects.alias(full_name=Concat(...)).filter(F("full_name").ilike("%x%"))
```

`F` supports: `like`, `ilike`, `eq`, `ne`, `lt`, `lte`, `gt`, `gte`, and `==`, `!=`, `<`, `<=`, `>`, `>=`.

---

### `Subquery(queryset)`

Wrap a QuerySet for use as RHS in expressions (e.g. `IN`, `=`). The subquery may reference outer columns via `OuterRef`.

```python
User.objects.filter(User.id.in_(Subquery(Order.objects.columns("user_id"))))
```

---

### `OuterRef(ref)`

Reference a column from the outer query when inside a subquery. `ref` can be a `BoundColumnRef` (e.g. `User.id`) or attribute name string.

```python
Order.objects.filter(Order.user_id == OuterRef(User.id))
```

---

## Column lookups (BoundColumnRef)

When you access a model field on the class (e.g. `User.email`), you get a `BoundColumnRef`. It supports:

| Method / operator | SQL |
|-------------------|-----|
| `==`, `!=`, `<`, `<=`, `>`, `>=` | `=`, `!=`, `<`, `<=`, `>`, `>=` |
| `.like(pattern)` | `LIKE` |
| `.ilike(pattern)` | `ILIKE` |
| `.in_(iterable)` | `IN (...)` |
| `.in_(Subquery(...))` | `IN (SELECT ...)` |

---

## Aggregates

| Function | Description | Example |
|----------|-------------|---------|
| `Min(column)` | Minimum | `Min(Product.price)` |
| `Max(column)` | Maximum | `Max(Product.price)` |
| `Count(column=None)` | Count rows or non-null | `Count()`, `Count(User.id)` |
| `Sum(column)` | Sum | `Sum(Order.total)` |
| `Avg(column)` | Average | `Avg(Product.rating)` |

Use with `QuerySet.aggregate()`.

---

## SQL Functions

Use in `annotate()`, `alias()`, or filters.

### String

| Function | Description |
|----------|-------------|
| `Concat(*args)` | `CONCAT(str1, str2, ...)` |
| `Upper(expr)` | `UPPER(text)` |
| `Lower(expr)` | `LOWER(text)` |
| `Length(expr)` | `LENGTH(text)` |
| `Trim(expr, chars=None)` | `TRIM([chars FROM] text)` |
| `Replace(expr, from_str, to_str)` | `REPLACE(string, from, to)` |

### General

| Function | Description |
|----------|-------------|
| `Coalesce(*args)` | First non-NULL |
| `NullIf(a, b)` | NULL if a=b |

### Math

| Function | Description |
|----------|-------------|
| `Abs(expr)` | Absolute value |
| `Round(expr, precision=0)` | Round |
| `Floor(expr)` | Floor |
| `Ceil(expr)` | Ceiling |

### Date/time

| Function | Description |
|----------|-------------|
| `Now()` | Current timestamp |
| `CurrentDate()` | Current date |
| `CurrentTimestamp()` | Current timestamp |
| `DateTrunc(field, expr)` | Truncate to field (e.g. `"month"`) |

### Generic

```python
Func_("function_name", arg1, arg2, ...)
```

Use for any PostgreSQL function not listed above.

---

## CompiledQuery

Returned by `QuerySet.compiled()`. Not part of the public API but useful for debugging.

| Attribute | Type | Description |
|-----------|------|-------------|
| `sql` | `psycopg.sql.Composable` | SQL composable (use `.as_string(None)` for string) |
| `params` | `list` | Ordered parameter values |
