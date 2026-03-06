# Subqueries

## Subquery

Wrap a QuerySet to use it as the right-hand side of an expression (e.g. `IN`, `=`, `EXISTS`):

```python
from pgstorm import Subquery

# Users whose id is in the list of user_ids from orders
User.objects.filter(
    User.id.in_(Subquery(Order.objects.columns("user_id")))
)
```

The subquery must return a single column (use `columns("col")` to select one).

## OuterRef

Reference a column from the **outer** query when inside a subquery. Used for correlated subqueries:

```python
from pgstorm import Subquery, OuterRef

# Users who have at least one order
User.objects.filter(
    User.id.in_(
        Subquery(
            Order.objects
                .filter(Order.user_id == OuterRef(User.id))
                .columns("user_id")
        )
    )
)
```

`OuterRef(User.id)` refers to the `User.id` from the outer query when the subquery is evaluated for each row.

### OuterRef with attribute name

You can also pass a string (attribute name) if the context is clear:

```python
OuterRef("id")  # when the outer model's id is implied
```

## Correlated Subquery Example

Find users who have at least one order (the classic "exists" pattern):

```python
User.objects.filter(
    User.id.in_(
        Subquery(
            Order.objects
                .filter(Order.user_id == OuterRef(User.id))
                .columns("user_id")
        )
    )
)
```

The subquery returns `user_id` for each order; `OuterRef(User.id)` ensures we only match orders belonging to the current user in the outer query.

## EXISTS

Subqueries can be used in EXISTS patterns when the parser supports it—typically by using a subquery in a filter that compiles to `EXISTS (SELECT ...)`.

## CTEs

Use `as_cte(name)` to turn a QuerySet into a Common Table Expression:

```python
active_users = User.objects.filter(User.active).as_cte("active_users")
# Use active_users in a larger query
```
