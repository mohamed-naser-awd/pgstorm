# Models & Types

## Defining Models

Subclass `BaseModel` and annotate attributes with `types`:

```python
from pgstorm import BaseModel, types

class Product(BaseModel):
    __table__ = "products"
    name: types.String
    price: types.Integer
    created_at: types.String  # or use a datetime type when available
```

## Table Names

- `__table__` or `__tablename__` — explicit table name
- Otherwise, the class name lowercased is used (e.g. `Product` → `product`)

## Scalar Types

| Type | PostgreSQL | Python |
|------|------------|--------|
| `types.Integer` | INTEGER | int |
| `types.String` | TEXT | str |

## Relation Types

### ForeignKey

```python
class Order(BaseModel):
    __table__ = "orders"
    user: types.ForeignKey[User]  # references User
```

### With Metadata

```python
# ON DELETE behavior
user: types.ForeignKey[User, types.ON_DELETE_CASCADE]
user: types.ForeignKey[User, types.ON_DELETE_RESTRICT]
user: types.ForeignKey[User, types.ON_DELETE_SET_NULL]
user: types.ForeignKey[User, types.ON_DELETE_NO_ACTION]

# Reference a specific field (e.g. email instead of id)
user: types.ForeignKey[User, types.ON_DELETE_CASCADE, types.FK_FIELD("email")]
```

### OneToOne and ManyToMany

```python
profile: types.OneToOne[User]
tags: types.ManyToMany[Tag]
```

### Self-referential relations

```python
reply_to: types.ForeignKey[types.Self]
```

## Custom field types

You can define custom column types by subclassing `Field` and (optionally) `Column`. Use a custom `Column` when you need a specific PostgreSQL type or custom lookups; otherwise reuse an existing column class.

**Example: `ImageField`** — store an image path/URL in a `VARCHAR(500)` column:

```python
from pgstorm import BaseModel, types
from pgstorm.columns.base import Column, Field


class ImageColumn(Column):
    def __init__(self, name: str = "", **kwargs):
        super().__init__(name=name, pg_type="VARCHAR(500)", python_type=str, **kwargs)


class ImageField(Field):
    column_class = ImageColumn

    def _make_column(self):
        return self.column_class(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class Product(BaseModel):
    __table__ = "products"
    name: types.String
    image_url: ImageField
```

- **`column_class`** — the `Column` subclass used for DDL and query expressions.
- **`_make_column()`** — builds the column instance; override to pass custom args (e.g. length) from the descriptor to the column.
- Use as **type** (`image_url: ImageField`) or as **instance** if your field takes options (`image_url: ImageField(max_length=1000)` — then your descriptor’s `__init__` would accept `max_length` and pass it in `_make_column()`).

## Accessing Columns

On the model class, attributes return `BoundColumnRef` for use in queries:

```python
User.email        # column reference
User.age > 18     # Expression
User.email.like("%@example.com")
User.id.in_([1, 2, 3])
```

For relations, chain to the related model's columns:

```python
UserProfile.user.email  # UserProfile.user -> User, then User.email
```
