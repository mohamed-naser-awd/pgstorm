# Functions & Aggregates

## SQL Functions

Use these in `annotate()`, `alias()`, or directly in expressions. All accept column references (`User.email`) or nested `Func` results.

### String

| Function | Description | Example |
|----------|-------------|---------|
| `Concat(*args)` | Concatenate strings | `Concat(User.first_name, " ", User.last_name)` |
| `Upper(expr)` | Uppercase | `Upper(User.email)` |
| `Lower(expr)` | Lowercase | `Lower(User.name)` |
| `Length(expr)` | String length | `Length(User.bio)` |
| `Trim(expr, chars?)` | Trim whitespace (or chars) | `Trim(User.name)` |
| `Replace(expr, from, to)` | Replace substring | `Replace(User.title, "Mr", "Mr.")` |

### General

| Function | Description | Example |
|----------|-------------|---------|
| `Coalesce(*args)` | First non-NULL | `Coalesce(User.nickname, User.name)` |
| `NullIf(a, b)` | NULL if a=b | `NullIf(User.score, 0)` |

### Math

| Function | Description | Example |
|----------|-------------|---------|
| `Abs(expr)` | Absolute value | `Abs(Product.discount)` |
| `Round(expr, precision?)` | Round | `Round(Product.price, 2)` |
| `Floor(expr)` | Floor | `Floor(Product.quantity)` |
| `Ceil(expr)` | Ceiling | `Ceil(Product.quantity)` |

### Date/Time

| Function | Description | Example |
|----------|-------------|---------|
| `Now()` | Current timestamp | `Now()` |
| `CurrentDate()` | Current date | `CurrentDate()` |
| `CurrentTimestamp()` | Current timestamp | `CurrentTimestamp()` |
| `DateTrunc(field, expr)` | Truncate to field | `DateTrunc("month", Order.created_at)` |

### Generic

For any PostgreSQL function not listed:

```python
from pgstorm import Func_

Func_("my_function", User.col1, User.col2, "literal")
```

## Aggregates

| Function | Description | Example |
|----------|-------------|---------|
| `Min(col)` | Minimum | `Min(Product.price)` |
| `Max(col)` | Maximum | `Max(Product.price)` |
| `Count(col?)` | Count rows or non-null | `Count()`, `Count(User.id)` |
| `Sum(col)` | Sum | `Sum(Order.total)` |
| `Avg(col)` | Average | `Avg(Product.rating)` |

Use with `aggregate()`:

```python
Product.objects.aggregate(
    Min(Product.price),
    Max(Product.price),
    total=Sum(Product.price),
    row_count=Count()
)
```

## Usage in Annotate

```python
User.objects.annotate(
    full_name=Concat(User.first_name, " ", User.last_name),
    upper_email=Upper(User.email)
)
```

## Usage in Alias + F

```python
User.objects.alias(
    full_name=Concat(User.first_name, " ", User.last_name)
).filter(F("full_name").ilike("%x%"))
```
