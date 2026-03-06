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
