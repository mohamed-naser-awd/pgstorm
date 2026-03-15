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

**Resolving DB values to Python types:** override `to_python(value)` to convert the raw DB value when the attribute is read, and `to_db(value)` to convert when the attribute is set or persisted. The descriptor stores the DB form internally; `to_python` / `to_db` give you a Pythonic type (e.g. `S3Media`) while the column stays a simple type (e.g. `VARCHAR`).

**Example: `ImageField`** — store an image URL in `VARCHAR(500)` and expose it as an `S3Media` instance:

```python
from pgstorm import BaseModel, types
from pgstorm.columns.base import Column, Field


class S3Media:
    """Pythonic wrapper for an S3 path/URL stored as string in the DB."""
    def __init__(self, url: str):
        self.url = url
    def __str__(self) -> str:
        return self.url


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

    def to_python(self, value):
        """DB string -> S3Media when reading the attribute."""
        if value is None:
            return None
        return S3Media(value) if isinstance(value, str) else value

    def to_db(self, value):
        """S3Media or str -> string for storage and INSERT/UPDATE."""
        if value is None:
            return None
        return getattr(value, "url", value) if not isinstance(value, str) else value


class Product(BaseModel):
    __table__ = "products"
    name: types.String
    image_url: ImageField
```

Usage: the DB column is a string; on the instance you get and set a rich type:

```python
product = Product.objects.filter(Product.id == 1)[0]
media = product.image_url   # S3Media instance
print(media.url)            # "s3://bucket/key.png"

product.image_url = S3Media("s3://bucket/new.png")
await product.update()      # persists the URL string
```

- **`column_class`** — the `Column` subclass used for DDL and query expressions.
- **`_make_column()`** — builds the column instance; override to pass custom args (e.g. length) from the descriptor to the column.
- **`to_python(value)`** — raw value from DB → Python type when the attribute is read.
- **`to_db(value)`** — Python value → raw form when the attribute is set or when building row data for INSERT/UPDATE.
- Use as **type** (`image_url: ImageField`) or as **instance** if your field takes options (`image_url: ImageField(max_length=1000)`).

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
