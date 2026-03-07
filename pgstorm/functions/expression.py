from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional, Type


class BoundColumnRef:
    """
    Left-hand side for expressions: carries (model, attr_name) so SQL can always
    be compiled to "table"."column" without resolving by column identity.
    Returned by Field when accessed on the model class (e.g. User.email).
    When representing a relation (FK), target_model is set so attribute access
    (e.g. .email) resolves to the related model's column.
    """

    __slots__ = ("model", "attr_name", "column", "target_model", "relation_attr")

    def __init__(
        self,
        model: type[Any],
        attr_name: str,
        column: Any,
        *,
        target_model: Optional[Type[Any]] = None,
        relation_attr: Optional[str] = None,
    ) -> None:
        self.model = model
        self.attr_name = attr_name
        self.column = column
        self.target_model = target_model
        self.relation_attr = relation_attr

    def _expr(self, operator: str, rhs: Any) -> Expression:
        return Expression(self, operator, rhs)

    # Common lookups so expressions use this ref as lhs (not the raw column)
    def like(self, pattern: str) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.LIKE, pattern)

    def ilike(self, pattern: str) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.ILIKE, pattern)

    def eq(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.EQ, rhs)

    def ne(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.NE, rhs)

    def lt(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.LT, rhs)

    def lte(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.LTE, rhs)

    def gt(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.GT, rhs)

    def gte(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.GTE, rhs)

    def __eq__(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.EQ, rhs)

    def __ne__(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.NE, rhs)

    def __lt__(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.LT, rhs)

    def __le__(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.LTE, rhs)

    def __gt__(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.GT, rhs)

    def __ge__(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.GTE, rhs)

    def __add__(self, rhs: Any) -> Expression:
        return Expression(self, "+", _resolve_rhs_for_arithmetic(rhs))

    def __radd__(self, lhs: Any) -> Expression:
        return Expression(_resolve_rhs_for_arithmetic(lhs), "+", self)

    def __sub__(self, rhs: Any) -> Expression:
        return Expression(self, "-", _resolve_rhs_for_arithmetic(rhs))

    def __rsub__(self, lhs: Any) -> Expression:
        return Expression(_resolve_rhs_for_arithmetic(lhs), "-", self)

    def __mul__(self, rhs: Any) -> Expression:
        return Expression(self, "*", _resolve_rhs_for_arithmetic(rhs))

    def __rmul__(self, lhs: Any) -> Expression:
        return Expression(_resolve_rhs_for_arithmetic(lhs), "*", self)

    def __truediv__(self, rhs: Any) -> Expression:
        return Expression(self, "/", _resolve_rhs_for_arithmetic(rhs))

    def __rtruediv__(self, lhs: Any) -> Expression:
        return Expression(_resolve_rhs_for_arithmetic(lhs), "/", self)

    def __getattr__(self, name: str) -> Any:
        # If this ref is for a relation (FK), resolve name on the related model first
        if self.target_model is not None:
            from pgstorm.columns.base import Field

            # Get the raw descriptor from the model's dict to avoid triggering __get__
            attr = self.target_model.__dict__.get(name)
            if isinstance(attr, Field):
                col = attr.get_column() or attr._make_column()
                return BoundColumnRef(self.target_model, name, col)
            # Also accept if already a BoundColumnRef (e.g. from another chain)
            if isinstance(getattr(self.target_model, name, None), BoundColumnRef):
                return getattr(self.target_model, name)
        # Delegate to column (e.g. custom lookups); rebuild Expression with self as lhs
        val = getattr(self.column, name)
        if callable(val):
            def with_ref(rhs: Any) -> Expression:
                e = val(rhs)
                if isinstance(e, Expression):
                    return Expression(self, e.operator, e.rhs)
                return e
            return with_ref
        return val

    def __repr__(self) -> str:
        model_name = getattr(self.model, "__name__", str(self.model))
        attr = self.attr_name or "?"
        return f"BoundColumnRef({model_name}.{attr})"


@dataclass(frozen=True, slots=True)
class Expression:
    lhs: Any  # BoundColumnRef | Column | (table_name, column_name) for clear SQL
    operator: str
    rhs: Any

    def __repr__(self) -> str:  # pragma: no cover
        return f"Expression(lhs={self.lhs!r}, operator={self.operator!r}, rhs={self.rhs!r})"


@dataclass(frozen=True, slots=True)
class AndExpression:
    expressions: list[Expression | AndExpression | OrExpression | NotExpression]

    def __repr__(self) -> str:  # pragma: no cover
        return f"AndExpression(expressions={self.expressions!r})"


@dataclass(frozen=True, slots=True)
class OrExpression:
    expressions: list[Expression | AndExpression | OrExpression | NotExpression]

    def __repr__(self) -> str:  # pragma: no cover
        return f"OrExpression(expressions={self.expressions!r})"


@dataclass(frozen=True, slots=True)
class NotExpression:
    expression: Expression | AndExpression | OrExpression

    def __repr__(self) -> str:  # pragma: no cover
        return f"NotExpression(expression={self.expression!r})"


class Q:
    """
    Wraps filter expressions for use in filter(). Supports | (OR), & (AND), ~ (NOT).

    Examples:
        Q(User.age > 18) | Q(User.age < 5)   -> OR
        Q(User.age > 18) & Q(User.active)    -> AND
        ~Q(User.deleted)                     -> NOT
    """

    __slots__ = ("expression",)

    def __init__(self, expression: Expression | AndExpression | OrExpression | NotExpression) -> None:
        self.expression = expression

    def __or__(self, other: "Q") -> "Q":
        if not isinstance(other, Q):
            return NotImplemented
        return Q(OrExpression([self.expression, other.expression]))

    def __and__(self, other: "Q") -> "Q":
        if not isinstance(other, Q):
            return NotImplemented
        return Q(AndExpression([self.expression, other.expression]))

    def __invert__(self) -> "Q":
        return Q(NotExpression(self.expression))


def _to_expression(obj: Q | Expression | AndExpression | OrExpression | NotExpression) -> Expression | AndExpression | OrExpression | NotExpression:
    """Extract the underlying expression from Q, or return as-is."""
    return obj.expression if isinstance(obj, Q) else obj


def and_(*conditions: Q | Expression | AndExpression | OrExpression | NotExpression) -> Q:
    """Combine conditions with AND. E.g. and_(Q(a), Q(b), c) -> (a AND b AND c)."""
    if not conditions:
        raise ValueError("and_() requires at least one condition")
    exprs = [_to_expression(c) for c in conditions]
    return Q(AndExpression(exprs))


def or_(*conditions: Q | Expression | AndExpression | OrExpression | NotExpression) -> Q:
    """Combine conditions with OR. E.g. or_(Q(a), Q(b), c) -> (a OR b OR c)."""
    if not conditions:
        raise ValueError("or_() requires at least one condition")
    exprs = [_to_expression(c) for c in conditions]
    return Q(OrExpression(exprs))


def not_(condition: Q | Expression | AndExpression | OrExpression | NotExpression) -> Q:
    """Negate a condition. E.g. not_(Q(a)) -> NOT a."""
    return Q(NotExpression(_to_expression(condition)))


def _resolve_rhs_for_arithmetic(rhs: Any) -> Any:
    """Convert Python literals to Value when used in arithmetic. Value and combinables pass through."""
    if isinstance(rhs, (BoundColumnRef, F, Value)):
        return rhs
    if isinstance(rhs, Expression) and rhs.operator in ("+", "-", "*", "/"):
        return rhs
    # Infer output_field from Python type for common literals
    if isinstance(rhs, int):
        from pgstorm import types
        return Value(rhs, output_field=types.Integer)
    if isinstance(rhs, float):
        return Value(rhs, output_field=None)
    if isinstance(rhs, (str, bytes)):
        from pgstorm import types
        return Value(rhs, output_field=types.String)
    return Value(rhs, output_field=None)


class Value:
    """
    Wraps a literal value for use in expressions. Use when you need explicit output_field.
    Literals in arithmetic (e.g. F(col) + 100) are automatically wrapped in Value.
    """
    __slots__ = ("value", "output_field")

    def __init__(self, value: Any, *, output_field: Any = None) -> None:
        self.value = value
        self.output_field = output_field

    def _expr(self, operator: str, rhs: Any) -> Expression:
        return Expression(self, operator, rhs)

    def __add__(self, rhs: Any) -> Expression:
        return Expression(self, "+", _resolve_rhs_for_arithmetic(rhs))

    def __radd__(self, lhs: Any) -> Expression:
        return Expression(_resolve_rhs_for_arithmetic(lhs), "+", self)

    def __sub__(self, rhs: Any) -> Expression:
        return Expression(self, "-", _resolve_rhs_for_arithmetic(rhs))

    def __rsub__(self, lhs: Any) -> Expression:
        return Expression(_resolve_rhs_for_arithmetic(lhs), "-", self)

    def __mul__(self, rhs: Any) -> Expression:
        return Expression(self, "*", _resolve_rhs_for_arithmetic(rhs))

    def __rmul__(self, lhs: Any) -> Expression:
        return Expression(_resolve_rhs_for_arithmetic(lhs), "*", self)

    def __truediv__(self, rhs: Any) -> Expression:
        return Expression(self, "/", _resolve_rhs_for_arithmetic(rhs))

    def __rtruediv__(self, lhs: Any) -> Expression:
        return Expression(_resolve_rhs_for_arithmetic(lhs), "/", self)

    def __repr__(self) -> str:
        return f"Value({self.value!r}, output_field={self.output_field!r})"


class F:
    """
    Reference to a field or annotation/alias by name. Use in filter/order_by/annotate.
    - F("alias_name") resolves to an annotation or alias (e.g. in filter).
    - F(Model.column) references a column directly for use in annotate expressions.

    Example:
        Model.objects.alias(full_name=Concat(...)).filter(F("full_name").ilike("%x%"))
        Model.objects.annotate(extra_value=F(User.age) + 100)
    """

    __slots__ = ("name",)

    def __init__(self, name: str | BoundColumnRef) -> None:
        self.name = name

    def _expr(self, operator: str, rhs: Any) -> Expression:
        return Expression(self, operator, rhs)

    def like(self, pattern: str) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.LIKE, pattern)

    def ilike(self, pattern: str) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.ILIKE, pattern)

    def eq(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.EQ, rhs)

    def ne(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.NE, rhs)

    def lt(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.LT, rhs)

    def lte(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.LTE, rhs)

    def gt(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.GT, rhs)

    def gte(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.GTE, rhs)

    def __eq__(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.EQ, rhs)

    def __ne__(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.NE, rhs)

    def __lt__(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.LT, rhs)

    def __le__(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.LTE, rhs)

    def __gt__(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.GT, rhs)

    def __ge__(self, rhs: Any) -> Expression:
        from pgstorm import operator as op
        return self._expr(op.GTE, rhs)

    def __add__(self, rhs: Any) -> Expression:
        return Expression(self, "+", _resolve_rhs_for_arithmetic(rhs))

    def __radd__(self, lhs: Any) -> Expression:
        return Expression(_resolve_rhs_for_arithmetic(lhs), "+", self)

    def __sub__(self, rhs: Any) -> Expression:
        return Expression(self, "-", _resolve_rhs_for_arithmetic(rhs))

    def __rsub__(self, lhs: Any) -> Expression:
        return Expression(_resolve_rhs_for_arithmetic(lhs), "-", self)

    def __mul__(self, rhs: Any) -> Expression:
        return Expression(self, "*", _resolve_rhs_for_arithmetic(rhs))

    def __rmul__(self, lhs: Any) -> Expression:
        return Expression(_resolve_rhs_for_arithmetic(lhs), "*", self)

    def __truediv__(self, rhs: Any) -> Expression:
        return Expression(self, "/", _resolve_rhs_for_arithmetic(rhs))

    def __rtruediv__(self, lhs: Any) -> Expression:
        return Expression(_resolve_rhs_for_arithmetic(lhs), "/", self)

    def __repr__(self) -> str:
        return f"F({self.name!r})"


class OuterRef:
    """
    Reference to a column from the outer query when used inside a subquery.
    Use with Subquery to create correlated subqueries.

    Example:
        User.objects.filter(
            User.id.in_(
                Subquery(
                    Order.objects.filter(Order.user_id == OuterRef(User.id)).columns("user_id")
                )
            )
        )
    """

    __slots__ = ("ref",)

    def __init__(self, ref: BoundColumnRef | str) -> None:
        """ref: BoundColumnRef (e.g. User.id) or attribute name string (e.g. "id")."""
        self.ref = ref

    def __repr__(self) -> str:
        return f"OuterRef({self.ref!r})"


class Subquery:
    """
    Wraps a QuerySet for use as RHS in expressions (e.g. IN, =, EXISTS).
    The subquery may reference outer columns via OuterRef.

    Example:
        User.objects.filter(
            User.id.in_(Subquery(Order.objects.filter(Order.user_id == OuterRef(User.id)).columns("user_id")))
        )
    """

    __slots__ = ("queryset",)

    def __init__(self, queryset: Any) -> None:
        from pgstorm.queryset.base import QuerySet

        if not isinstance(queryset, QuerySet):
            raise TypeError(f"Subquery requires a QuerySet, got {type(queryset).__name__}")
        self.queryset = queryset

    def __repr__(self) -> str:
        return f"Subquery({self.queryset!r})"


@dataclass(frozen=True, slots=True)
class JoinExpression:
    lhs: str
    rhs: str
    on: Expression
    join_type: Literal["LEFT", "RIGHT", "INNER", "FULL", "LATERAL"]
    rhs_model: type[Any] | None = None  # optional, for ON-clause column resolution
    lhs_schema: str | None = None
    rhs_schema: str | None = None

    def __repr__(self) -> str:  # pragma: no cover
        return f"JoinExpression(lhs={self.lhs!r}, rhs={self.rhs!r}, on={self.on!r}, join_type={self.join_type!r})"
