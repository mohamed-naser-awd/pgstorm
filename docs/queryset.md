# QuerySet API

## Overview

Every model has an `objects` manager that returns a `QuerySet`. QuerySets are lazy—they only execute when you iterate, index, or call `fetch()`.

## Filtering

### Comparisons

```python
User.objects.filter(User.age >= 18)
User.objects.filter(User.email == "a@b.com")
User.objects.filter(User.id != 5)
User.objects.filter(User.price < 100)
```

### LIKE / ILIKE

```python
User.objects.filter(User.email.like("%@example.com"))
User.objects.filter(User.name.ilike("%john%"))  # case-insensitive
```

### IN

```python
User.objects.filter(User.id.in_([1, 2, 3]))
User.objects.filter(User.id.in_(Subquery(Order.objects.columns("user_id"))))
```

### Exclude

```python
User.objects.filter(User.age > 18).exclude(User.deleted)
```

## Q Objects

Combine conditions with `|` (OR), `&` (AND), `~` (NOT):

```python
from pgstorm import Q, and_, or_, not_

User.objects.filter(Q(User.age > 18) | Q(User.age < 5))
User.objects.filter(and_(Q(User.active), Q(User.verified)))
User.objects.filter(~Q(User.deleted))
```

## Joins

```python
UserProfile.objects.join(
    User,
    UserProfile.user.email == User.email,
    join_type="LEFT"  # LEFT, RIGHT, INNER, FULL, LATERAL
)
```

## Schemas

```python
User.objects.using_schema("tenant_1").filter(...)
UserProfile.objects.join(User, ..., rhs_schema="tenant_2")
```

## Ordering & Pagination

```python
User.objects.order_by(User.age)
User.objects.limit(10).offset(20)
```

## Column Selection

```python
User.objects.columns("id", "email")   # SELECT only these
User.objects.defer("password")        # exclude column(s)
User.objects.distinct()              # SELECT DISTINCT
```

## Aggregates

```python
from pgstorm import Min, Max, Count, Sum, Avg

Product.objects.aggregate(Min(Product.price), Max(Product.price))
Product.objects.aggregate(total=Sum(Product.price), cnt=Count())
Product.objects.aggregate(row_count=Count())  # COUNT(*)
```

## Annotate

Add computed columns to the SELECT clause. Results include these values:

```python
from pgstorm import Concat

User.objects.annotate(full_name=Concat(User.first_name, " ", User.last_name))
# Each row has .full_name
```

## Alias

Define expressions for use in `filter` or `order_by` without including them in SELECT:

```python
from pgstorm import Concat, F

User.objects.alias(full_name=Concat(User.first_name, " ", User.last_name)).filter(
    F("full_name").ilike("%mohamed%")
)
```

## Get

```python
user = User.objects.get(User.id == 1)  # raises if not found or multiple
```

## Compiling

```python
compiled = qs.compiled()
print(compiled.sql.as_string())
print(compiled.params)

sql, params = qs.as_sql()
cursor.execute(sql, params)
```

## CTEs

```python
qs = User.objects.filter(User.active).as_cte("active_users")
# Use in another query...
```
