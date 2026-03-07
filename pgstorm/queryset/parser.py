from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, List, TYPE_CHECKING

from psycopg import sql

from pgstorm.columns.base import Column, Field, RelationField, _model_primary_key_field
from pgstorm.functions.aggregate import Aggregate
from pgstorm.functions.expression import (
    AndExpression,
    BoundColumnRef,
    Expression,
    F,
    JoinExpression,
    NotExpression,
    OrExpression,
    OuterRef,
    Subquery,
    Value,
)
from pgstorm.functions.func import Func
from pgstorm import operator as op

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from pgstorm.queryset.base import QuerySet


@dataclass(frozen=True, slots=True)
class RawQuery:
    """
    Container for raw SQL execution.
    Used by engine.raw_execute(query, params).
    """

    sql: str
    params: List[Any] = field(default_factory=list)
    action: str = "raw_sql"
    model: type[Any] | None = None
    table: str | None = None
    extra: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CompiledQuery:
    """
    Simple container for a compiled queryset.

    - sql: a psycopg3 SQL composable object (sql.Composable).
    - params: the list of parameters in order.
    - action: observer action (fetch, create, update, delete, etc.).
    - model: model class for table-specific observers.
    - table: table name for observer context.
    - extra: additional data for observers (e.g. objs, fields).
    """

    sql: sql.Composable
    params: List[Any]
    action: str = "query"
    model: type[Any] | None = None
    table: str | None = None
    extra: dict[str, Any] | None = None


def _table_name(model: type[Any]) -> str:
    """
    Resolve the database table name for a model.

    - Prefer explicit __tablename__ if present.
    - Fallback to lowercased class name.
    """

    explicit = getattr(model, "__tablename__", None) or getattr(model, "__table__", None)
    if isinstance(explicit, str) and explicit:
        return explicit
    return model.__name__.lower()


def _iter_model_columns(model: type[Any]) -> Iterable[tuple[str, Column]]:
    """
    Yield (attribute_name, Column) for each field on the model (including base classes).
    Uses the model's attribute name as the column name so we never rely on empty column.name.
    """

    from pgstorm.columns.base import Field

    seen: set[str] = set()
    for cls in model.__mro__:
        if cls is object:
            continue
        for attr_name, attr_value in vars(cls).items():
            if attr_name.startswith("_") or attr_name in seen:
                continue
            if isinstance(attr_value, Field):
                column = attr_value.get_column()
                if column is not None:
                    seen.add(attr_name)
                    yield (attr_name, column)


def _resolve_column_name(model: type[Any], column: Any) -> str | None:
    """
    Resolve the database column name for a column instance by finding which
    model attribute holds this column (by identity). Use when column.name is empty.
    """
    for attr_name, col in _iter_model_columns(model):
        if col is column:
            return attr_name
    return None


def _db_column_name(ref: Any, model: type[Any] | None = None, rhs_model: type[Any] | None = None) -> str:
    """
    Get the actual DB column name for SQL. Prefers column.name (e.g. user_id for FK)
    over attr_name (e.g. user). Use this when building SQL identifiers.
    """
    if isinstance(ref, BoundColumnRef):
        col = getattr(ref, "column", None)
        if col and getattr(col, "name", None):
            return col.name
        return ref.attr_name or _resolve_column_name(ref.model, col) or ""
    if isinstance(ref, Column):
        if getattr(ref, "name", None):
            return ref.name
        return (model and _resolve_column_name(model, ref)) or (rhs_model and _resolve_column_name(rhs_model, ref)) or ""
    return getattr(ref, "attr_name", None) or getattr(ref, "name", None) or ""


def _attr_to_db_column_name(model: type[Any], attr_name: str) -> str:
    """Resolve model attribute name to DB column name. Falls back to attr_name if not found."""
    for name, col in _iter_model_columns(model):
        if name == attr_name:
            return col.name if getattr(col, "name", None) else attr_name
    return attr_name


def _compile_aggregate(
    agg: Aggregate,
    alias: str,
    table: str,
    model: type[Any],
    params: List[Any],
    *,
    annotations: dict[str, Any] | None = None,
    aliases: dict[str, Any] | None = None,
) -> sql.Composable:
    """Compile a single aggregate to SQL: FUNC(column) AS alias or FUNC(*) AS alias."""
    func_sql = sql.SQL(agg.func_name)
    if agg.column is None:
        # COUNT(*) - count all rows
        inner = sql.SQL("*")
    elif isinstance(agg.column, str):
        # Check if it's an annotation or alias (e.g. Count("extra_value") where extra_value was annotated)
        combined = {**(aliases or {}), **(annotations or {})}
        resolved = combined.get(agg.column)
        if resolved is not None:
            inner = _compile_value(
                resolved,
                table,
                params,
                None,
                model,
                None,
                annotations,
                aliases,
            )
        else:
            col_name = _attr_to_db_column_name(model, agg.column)
            inner = sql.Identifier(table, col_name)
    elif isinstance(agg.column, Func):
        inner = _compile_value(
            agg.column,
            table,
            params,
            None,
            model,
            None,
            annotations,
            aliases,
        )
    else:
        col_name = _db_column_name(agg.column, agg.column.model)
        tbl = _table_name(agg.column.model)
        inner = sql.Identifier(tbl, col_name)
    return func_sql + sql.SQL("(") + inner + sql.SQL(") AS ") + sql.Identifier(alias)


def _compile_group_by_ref(
    ref: Any,
    table: str,
    model: type[Any],
) -> sql.Composable:
    """Compile a single GROUP BY reference to a qualified SQL identifier."""
    if isinstance(ref, BoundColumnRef):
        col_name = _db_column_name(ref, ref.model)
        tbl = _table_name(ref.model)
        return sql.Identifier(tbl, col_name)
    if isinstance(ref, Column):
        col_name = _db_column_name(ref, model)
        return sql.Identifier(table, col_name)
    if isinstance(ref, str):
        col_name = _attr_to_db_column_name(model, ref)
        return sql.Identifier(table, col_name)
    col_name = _db_column_name(ref, model) or getattr(ref, "name", str(ref))
    return sql.Identifier(table, col_name)


def _compile_group_by_clause(
    qs: "QuerySet[Any]",
    table: str,
    model: type[Any],
) -> sql.Composable | None:
    """Compile the GROUP BY clause. Returns None when there is nothing to group."""
    group_by = getattr(qs, "_group_by", None)
    if not group_by:
        return None
    parts = [_compile_group_by_ref(ref, table, model) for ref in group_by]
    return sql.SQL(" GROUP BY ") + sql.SQL(", ").join(parts)


def _select_list_for_queryset(qs: "QuerySet[Any]", params: List[Any] | None = None) -> sql.Composable:
    """
    Build the SELECT column list for the queryset.

    - If qs._aggregates is set, use aggregate expressions.
    - Else if qs._columns is set, restrict to those names.
    - Otherwise include all model columns.
    - Apply qs._exclude_columns to drop columns.
    - Fallback to '*' if we cannot discover any columns.
    """
    model = qs.model
    table = _table_name(model)

    aggregates = getattr(qs, "_aggregates", None)
    group_by_cols = getattr(qs, "_group_by", None)
    if aggregates or group_by_cols:
        # With GROUP BY, only return group-by columns and aggregate expressions
        parts: list[sql.Composable] = []
        if group_by_cols:
            for ref in group_by_cols:
                parts.append(_compile_group_by_ref(ref, table, model))
        if aggregates:
            p = params if params is not None else []
            ann = getattr(qs, "_annotations", {}) or {}
            al = getattr(qs, "_aliases", {}) or {}
            for agg, alias in aggregates:
                parts.append(
                    _compile_aggregate(
                        agg, alias, table, model, p,
                        annotations=ann, aliases=al,
                    )
                )
        return sql.SQL(", ").join(parts)

    # Discover all columns by attribute name (never use SELECT *)
    all_columns = dict(_iter_model_columns(model))
    annotations = getattr(qs, "_annotations", None) or {}
    columns_set = set(qs._columns) if qs._columns else None

    if qs._columns:
        selected_names = [
            name for name in qs._columns
            if name in all_columns or name in annotations
        ]
    else:
        selected_names = list(all_columns.keys())

    # Apply deferred/excluded columns
    if qs._exclude_columns:
        excluded = set(qs._exclude_columns)
        selected_names = [name for name in selected_names if name not in excluded]

    if not selected_names:
        selected_names = list(model.__annotations__.keys())

    # Use actual DB column name (e.g. user_id for FK) not attr name (user)
    parts: list[sql.Composable] = []
    for attr_name in selected_names:
        col = all_columns.get(attr_name)
        if col is not None:
            db_name = (col.name if getattr(col, "name", None) else None) or attr_name
            parts.append(sql.Identifier(table, db_name))

    # Append joined model columns (for hydration when explicit joins have rhs_model)
    for join in getattr(qs, "_joins", []) or []:
        rhs_model = getattr(join, "rhs_model", None)
        if rhs_model is None:
            continue
        rhs_table = join.rhs
        rhs_schema = getattr(join, "rhs_schema", None)
        for attr_name, _ in _iter_model_columns(rhs_model):
            alias = f"{rhs_table}__{attr_name}"
            if columns_set is not None and alias not in columns_set:
                continue
            if rhs_schema:
                parts.append(
                    sql.Identifier(rhs_schema, rhs_table, attr_name)
                    + sql.SQL(" AS ")
                    + sql.Identifier(alias)
                )
            else:
                parts.append(
                    sql.Identifier(rhs_table, attr_name)
                    + sql.SQL(" AS ")
                    + sql.Identifier(alias)
                )

    # Append annotations: expr AS alias
    if annotations:
        ann_params: list[Any] = []
        for alias, expr in annotations.items():
            if columns_set is not None and alias not in columns_set:
                continue
            compiled = _compile_value(
                expr, table, params, None, model, None, annotations, getattr(qs, "_aliases", None) or {}
            )
            parts.append(compiled + sql.SQL(" AS ") + sql.Identifier(alias))

    return sql.SQL(", ").join(parts)


def _is_iterable_but_not_str(value: Any) -> bool:
    if isinstance(value, (str, bytes)):
        return False
    try:
        iter(value)
    except TypeError:
        return False
    return True


def _is_expression_value(value: Any) -> bool:
    """True if value should be compiled as SQL expression rather than a literal placeholder."""
    return isinstance(
        value,
        (
            Expression,
            NotExpression,
            AndExpression,
            OrExpression,
            Subquery,
            Func,
            BoundColumnRef,
            Column,
            Value,
        ),
    )


def _compile_dml_value(
    value: Any,
    table: str,
    params: List[Any],
    model: type[Any],
) -> sql.Composable:
    """
    Compile a value for INSERT VALUES or UPDATE SET.
    Handles expressions, subqueries, funcs, column refs, Value; otherwise uses placeholder.
    """
    if isinstance(value, Expression) and value.operator in ("+", "-", "*", "/"):
        return _compile_value(
            value,
            table,
            params,
            table_for_column=None,
            model=model,
            rhs_model=None,
        )
    if isinstance(value, (Expression, NotExpression, AndExpression, OrExpression)):
        return _compile_expression(
            value,
            table,
            params,
            model=model,
            outer_table=table,
            outer_model=model,
        )
    if isinstance(value, Subquery):
        sub_sql = _compile_subquery_sql(
            value.queryset,
            params,
            outer_table=table,
            outer_model=model,
        )
        return sql.SQL("(") + sub_sql + sql.SQL(")")
    if isinstance(value, (Func, BoundColumnRef, Column, Value, F)):
        return _compile_value(
            value,
            table,
            params,
            table_for_column=None,
            model=model,
            rhs_model=None,
        )
    params.append(value)
    return sql.Placeholder()


def _compile_value(
    expr: Any,
    table: str,
    params: List[Any],
    table_for_column: Callable[[Any], str] | None,
    model: type[Any] | None,
    rhs_model: type[Any] | None,
    annotations: dict[str, Any] | None = None,
    aliases: dict[str, Any] | None = None,
) -> sql.Composable:
    """Compile a value (column ref, Func, Value, arithmetic Expression, or literal) to SQL."""
    if isinstance(expr, Func):
        return _compile_func(expr, table, params, table_for_column, model, rhs_model, annotations, aliases)
    if isinstance(expr, BoundColumnRef):
        col_name = _db_column_name(expr, expr.model)
        tbl = (table_for_column(expr.column) if table_for_column else None) or _table_name(expr.model)
        return sql.Identifier(tbl, col_name)
    if isinstance(expr, Column):
        col_name = _db_column_name(expr, model, rhs_model)
        tbl = (table_for_column(expr) if table_for_column else None) or table
        return sql.Identifier(tbl, col_name)
    if isinstance(expr, Value):
        params.append(expr.value)
        return sql.Placeholder()
    if isinstance(expr, Expression) and expr.operator in ("+", "-", "*", "/"):
        lhs_sql = _compile_value(
            expr.lhs, table, params, table_for_column, model, rhs_model, annotations, aliases
        )
        rhs_sql = _compile_value(
            expr.rhs, table, params, table_for_column, model, rhs_model, annotations, aliases
        )
        return sql.SQL("(") + lhs_sql + sql.SQL(f" {expr.operator} ") + rhs_sql + sql.SQL(")")
    if isinstance(expr, F):
        if isinstance(expr.name, BoundColumnRef):
            return _compile_value(
                expr.name, table, params, table_for_column, model, rhs_model, annotations, aliases
            )
        combined = {**(aliases or {}), **(annotations or {})}
        resolved = combined.get(expr.name)
        if resolved is not None:
            return _compile_value(
                resolved, table, params, table_for_column, model, rhs_model, annotations, aliases
            )
        raise ValueError(f"Unknown annotation/alias: {expr.name!r}")
    # Literal
    params.append(expr)
    return sql.Placeholder()


def _compile_func(
    f: Func,
    table: str,
    params: List[Any],
    table_for_column: Callable[[Any], str] | None,
    model: type[Any] | None,
    rhs_model: type[Any] | None,
    annotations: dict[str, Any] | None = None,
    aliases: dict[str, Any] | None = None,
) -> sql.Composable:
    """Compile a Func to SQL: FUNC_NAME(arg1, arg2, ...)."""
    if f.func_name in ("CURRENT_DATE", "CURRENT_TIMESTAMP") and not f.args:
        return sql.SQL(f.func_name)
    arg_parts: list[sql.Composable] = []
    for a in f.args:
        arg_parts.append(
            _compile_value(a, table, params, table_for_column, model, rhs_model, annotations, aliases)
        )
    if not arg_parts:
        return sql.SQL(f.func_name + "()")
    inner = sql.SQL(", ").join(arg_parts)
    return sql.SQL(f.func_name) + sql.SQL("(") + inner + sql.SQL(")")


def _compile_expression(
    expr: Expression | NotExpression | AndExpression | OrExpression,
    table: str,
    params: List[Any],
    table_for_column: Callable[[Any], str] | None = None,
    model: type[Any] | None = None,
    rhs_model: type[Any] | None = None,
    outer_table: str | None = None,
    outer_model: type[Any] | None = None,
    annotations: dict[str, Any] | None = None,
    aliases: dict[str, Any] | None = None,
) -> sql.Composable:
    """
    Compile a single Expression, NotExpression, AndExpression, or OrExpression into SQL and append params.
    When table_for_column is provided (e.g. for JOIN ON), it maps column -> table name.
    When model/rhs_model are provided, use them to resolve column name when column.name is empty.
    When outer_table/outer_model are provided (inside a subquery), OuterRef resolves to outer_table.column.
    """

    if isinstance(expr, NotExpression):
        inner_sql = _compile_expression(
            expr.expression,
            table,
            params,
            table_for_column=table_for_column,
            model=model,
            rhs_model=rhs_model,
            outer_table=outer_table,
            outer_model=outer_model,
        )
        return sql.SQL("NOT (") + inner_sql + sql.SQL(")")

    if isinstance(expr, AndExpression):
        and_parts = []
        for e in expr.expressions:
            part = _compile_expression(
                e,
                table,
                params,
                table_for_column=table_for_column,
                model=model,
                rhs_model=rhs_model,
                outer_table=outer_table,
                outer_model=outer_model,
            )
            # Wrap OR in parens so "a OR b" AND c becomes "(a OR b) AND c"
            if isinstance(e, OrExpression):
                part = sql.SQL("(") + part + sql.SQL(")")
            and_parts.append(part)
        return sql.SQL(" AND ").join(and_parts) if and_parts else sql.SQL("1 = 1")

    if isinstance(expr, OrExpression):
        or_parts = [
            _compile_expression(
                e,
                table,
                params,
                table_for_column=table_for_column,
                model=model,
                rhs_model=rhs_model,
                outer_table=outer_table,
                outer_model=outer_model,
            )
            for e in expr.expressions
        ]
        return sql.SQL(" OR ").join(or_parts) if or_parts else sql.SQL("1 = 0")

    # Plain Expression: lhs can be column ref, F (alias/annotation), or Func.
    lhs = expr.lhs
    ann = annotations or {}
    al = aliases or {}
    combined = {**al, **ann}  # aliases first so annotate overrides for same key

    # F or Func: compile as value expression (e.g. CONCAT(...) ILIKE '%x%')
    lhs_part: sql.Composable | None = None
    if isinstance(lhs, F):
        if isinstance(lhs.name, BoundColumnRef):
            lhs_part = _compile_value(
                lhs.name, table, params, table_for_column, model, rhs_model, ann, al
            )
        else:
            resolved = combined.get(lhs.name)
            if resolved is None:
                raise ValueError(f"Unknown annotation/alias: {lhs.name!r}")
            lhs_part = _compile_value(
                resolved, table, params, table_for_column, model, rhs_model, ann, al
            )
    elif isinstance(lhs, Func):
        lhs_part = _compile_value(
            lhs, table, params, table_for_column, model, rhs_model, ann, al
        )

    if lhs_part is not None:
        operator = expr.operator.upper()
        rhs = expr.rhs
        if rhs is None and operator in (op.EQ, op.NE, "=", "!="):
            sql_op = " IS " if operator in (op.EQ, "=") else " IS NOT "
            return lhs_part + sql.SQL(sql_op) + sql.SQL("NULL")
        if operator == op.IN and _is_iterable_but_not_str(rhs):
            rhs_seq = list(rhs)
            if not rhs_seq:
                return sql.SQL("1 = 0")
            placeholders = [sql.Placeholder() for _ in rhs_seq]
            for v in rhs_seq:
                params.append(v)
            return lhs_part + sql.SQL(" IN (") + sql.SQL(", ").join(placeholders) + sql.SQL(")")
        if isinstance(rhs, Subquery):
            sub_sql = _compile_subquery_sql(rhs.queryset, params, outer_table=table, outer_model=model)
            return lhs_part + sql.SQL(f" {operator} (") + sub_sql + sql.SQL(")")
        if isinstance(rhs, OuterRef):
            if outer_table is None or outer_model is None:
                raise ValueError("OuterRef can only be used inside a Subquery filter")
            ref = rhs.ref
            rhs_col = _db_column_name(ref, ref.model) if isinstance(ref, BoundColumnRef) else str(ref)
            return lhs_part + sql.SQL(f" {operator} ") + sql.Identifier(outer_table, rhs_col)
        if isinstance(rhs, BoundColumnRef):
            rhs_tbl = _table_name(rhs.model)
            rhs_col = _db_column_name(rhs, rhs.model)
            return lhs_part + sql.SQL(f" {operator} ") + sql.Identifier(rhs_tbl, rhs_col)
        if isinstance(rhs, Column):
            rhs_col = rhs.name or (model and _resolve_column_name(model, rhs)) or (rhs_model and _resolve_column_name(rhs_model, rhs)) or ""
            rhs_tbl = (table_for_column(rhs) if table_for_column else None) or table
            return lhs_part + sql.SQL(f" {operator} ") + sql.Identifier(rhs_tbl, rhs_col)
        params.append(rhs)
        return lhs_part + sql.SQL(f" {operator} ") + sql.Placeholder()

    if isinstance(lhs, OuterRef):
        if outer_table is None or outer_model is None:
            raise ValueError("OuterRef can only be used inside a Subquery filter")
        ref = lhs.ref
        if isinstance(ref, BoundColumnRef):
            col_name = _db_column_name(ref, ref.model)
        else:
            col_name = str(ref)
        tbl = outer_table
    elif isinstance(lhs, BoundColumnRef):
        col_name = _db_column_name(lhs, lhs.model)
        tbl = (
            table_for_column(lhs.column) if table_for_column else None
        ) or _table_name(lhs.model)
    elif isinstance(lhs, Column):
        col_name = _db_column_name(lhs, model, rhs_model) or ""
        tbl = (table_for_column(lhs) if table_for_column else None) or table
    else:
        col_name = _db_column_name(lhs, model, rhs_model) or getattr(lhs, "name", str(lhs))
        tbl = (table_for_column(lhs) if table_for_column else None) or table
    operator = expr.operator.upper()
    rhs = expr.rhs

    col_ident = sql.Identifier(tbl, col_name)

    # Handle NULL comparisons specially
    if rhs is None and operator in (op.EQ, op.NE, "=", "!="):
        sql_op = " IS " if operator in (op.EQ, "=") else " IS NOT "
        return col_ident + sql.SQL(sql_op) + sql.SQL("NULL")

    # Handle IN with an iterable RHS
    if operator == op.IN and _is_iterable_but_not_str(rhs):
        rhs_seq = list(rhs)  # type: ignore[arg-type]
        if not rhs_seq:
            # Empty IN () is always false; represent as 1=0
            return sql.SQL("1 = 0")

        placeholders: list[sql.Composable] = []
        for value in rhs_seq:
            placeholders.append(sql.Placeholder())
            params.append(value)

        placeholder_sql = sql.SQL(", ").join(placeholders)
        return col_ident + sql.SQL(" IN (") + placeholder_sql + sql.SQL(")")

    # RHS is Subquery: col IN (SELECT ...) or col = (SELECT ...)
    if isinstance(rhs, Subquery):
        sub_sql = _compile_subquery_sql(rhs.queryset, params, outer_table=table, outer_model=model)
        return col_ident + sql.SQL(f" {operator} (") + sub_sql + sql.SQL(")")

    # RHS is OuterRef (inside subquery filter)
    if isinstance(rhs, OuterRef):
        if outer_table is None or outer_model is None:
            raise ValueError("OuterRef can only be used inside a Subquery filter")
        ref = rhs.ref
        if isinstance(ref, BoundColumnRef):
            rhs_col_name = _db_column_name(ref, ref.model)
        else:
            rhs_col_name = str(ref)
        rhs_ident = sql.Identifier(outer_table, rhs_col_name)
        return col_ident + sql.SQL(f" {operator} ") + rhs_ident

    # RHS is a column ref (e.g. JOIN ON left.col = right.col)
    if isinstance(rhs, BoundColumnRef):
        rhs_col_name = _db_column_name(rhs, rhs.model)
        rhs_tbl = _table_name(rhs.model)
        rhs_ident = sql.Identifier(rhs_tbl, rhs_col_name)
        return col_ident + sql.SQL(f" {operator} ") + rhs_ident
    if isinstance(rhs, Column):
        rhs_col_name = _db_column_name(rhs, model, rhs_model) or ""
        rhs_tbl = (table_for_column(rhs) if table_for_column else None) or table
        rhs_ident = sql.Identifier(rhs_tbl, rhs_col_name)
        return col_ident + sql.SQL(f" {operator} ") + rhs_ident

    # Default: simple binary operator with a single placeholder
    params.append(rhs)
    return col_ident + sql.SQL(f" {operator} ") + sql.Placeholder()


def _compile_subquery_sql(
    qs: "QuerySet[Any]",
    params: List[Any],
    *,
    outer_table: str,
    outer_model: type[Any],
) -> sql.Composable:
    """
    Compile a queryset as a subquery (SELECT ... FROM ... WHERE ...).
    Pass outer_table/outer_model so OuterRef in the subquery's filters resolves correctly.
    """
    from pgstorm.queryset.base import QuerySet

    model = qs.model
    table = _table_name(model)
    schema = getattr(qs, "_schema", None)

    select_list = _select_list_for_queryset(qs, params)

    # Auto-add JOINs for filters
    existing_rhs = {j.rhs_model for j in qs._joins if getattr(j, "rhs_model", None) is not None}
    agg_refs: list[BoundColumnRef] = []
    for agg, _ in getattr(qs, "_aggregates", []) or []:
        if agg.column is not None:
            agg_refs.extend(_collect_bound_column_refs(agg.column))
    auto_joins = _joins_needed_for_filters(model, table, qs._filters, extra_refs=agg_refs)
    joins_to_use = list(qs._joins)
    for j in auto_joins:
        if j.rhs_model is not None and j.rhs_model not in existing_rhs:
            joins_to_use.append(j)
            existing_rhs.add(j.rhs_model)

    parts: list[sql.Composable] = []
    parts.append(sql.SQL("SELECT "))
    if qs._distinct:
        parts.append(sql.SQL("DISTINCT "))
    parts.append(select_list)
    parts.append(sql.SQL(" FROM "))
    if schema:
        parts.append(sql.Identifier(schema, table))
    else:
        parts.append(sql.Identifier(table))

    for join in joins_to_use:
        parts.append(sql.SQL(f" {join.join_type} JOIN "))
        if getattr(join, "rhs_schema", None):
            parts.append(sql.Identifier(join.rhs_schema, join.rhs))
        else:
            parts.append(sql.Identifier(join.rhs))
        parts.append(sql.SQL(" ON "))
        on_resolver = _build_table_for_column(model, table, join.rhs_model, join.rhs)
        parts.append(
            _compile_expression(
                join.on,
                table,
                params,
                table_for_column=on_resolver,
                model=model,
                rhs_model=join.rhs_model,
            )
        )

    if qs._filters:
        where_fragments = []
        for f in qs._filters:
            frag = _compile_expression(
                f, table, params, model=model,
                outer_table=outer_table, outer_model=outer_model,
            )
            if isinstance(f, OrExpression):
                frag = sql.SQL("(") + frag + sql.SQL(")")
            where_fragments.append(frag)
        where_sql = sql.SQL(" AND ").join(where_fragments)
        parts.append(sql.SQL(" WHERE ") + where_sql)

    group_by_sql = _compile_group_by_clause(qs, table, model)
    if group_by_sql is not None:
        parts.append(group_by_sql)

    having_filters = getattr(qs, "_having", None)
    if having_filters:
        having_fragments: list[sql.Composable] = []
        for h in having_filters:
            frag = _compile_expression(h, table, params, model=model)
            if isinstance(h, OrExpression):
                frag = sql.SQL("(") + frag + sql.SQL(")")
            having_fragments.append(frag)
        parts.append(sql.SQL(" HAVING ") + sql.SQL(" AND ").join(having_fragments))

    if qs._order_by:
        order_parts = []
        for ob in qs._order_by:
            if isinstance(ob, Expression):
                lhs = ob.lhs
                direction = ob.operator.upper() if ob.operator else ""
            else:
                lhs = ob
                direction = ""
            if isinstance(lhs, BoundColumnRef):
                order_table = _table_name(lhs.model)
                col_name = _db_column_name(lhs, lhs.model)
            elif isinstance(lhs, Column):
                col_name = _db_column_name(lhs, model, None)
                order_table = table
            else:
                col_name = _db_column_name(lhs, model, None) or getattr(lhs, "name", str(lhs))
                order_table = table
            col_ident = sql.Identifier(order_table, col_name)
            if direction in ("ASC", "DESC"):
                order_parts.append(col_ident + sql.SQL(f" {direction}"))
            else:
                order_parts.append(col_ident)
        if order_parts:
            parts.append(sql.SQL(" ORDER BY ") + sql.SQL(", ").join(order_parts))

    if qs._limit:
        parts.append(sql.SQL(" LIMIT ") + sql.Placeholder())
        params.append(int(qs._limit))
    if qs._offset:
        parts.append(sql.SQL(" OFFSET ") + sql.Placeholder())
        params.append(int(qs._offset))

    return sql.Composed(parts)


def _collect_bound_column_refs(expr: Any) -> list[BoundColumnRef]:
    """Recursively collect all BoundColumnRefs from an expression (filter/order/aggregate)."""
    refs: list[BoundColumnRef] = []
    if isinstance(expr, BoundColumnRef):
        refs.append(expr)
    elif isinstance(expr, Expression):
        refs.extend(_collect_bound_column_refs(expr.lhs))
        refs.extend(_collect_bound_column_refs(expr.rhs))
    elif isinstance(expr, NotExpression):
        refs.extend(_collect_bound_column_refs(expr.expression))
    elif isinstance(expr, AndExpression):
        for e in expr.expressions:
            refs.extend(_collect_bound_column_refs(e))
    elif isinstance(expr, OrExpression):
        for e in expr.expressions:
            refs.extend(_collect_bound_column_refs(e))
    elif isinstance(expr, Func):
        for a in expr.args:
            refs.extend(_collect_bound_column_refs(a))
    # str: no refs
    return refs


def _find_relation_to_model(main_model: type[Any], target_model: type[Any]) -> tuple[str, str] | None:
    """
    Find the relation on main_model that points to target_model.
    Returns (relation_attr_name, fk_field_on_target) or None.
    fk_field_on_target is the target's field name used for the join (from FK_FIELD, or primary key).
    """
    for attr_name, attr_value in vars(main_model).items():
        if attr_name.startswith("_"):
            continue
        if isinstance(attr_value, RelationField) and attr_value._target_model is target_model:
            fk_field = attr_value._fk_field or _model_primary_key_field(target_model)
            return (attr_name, fk_field)
    return None


def _joins_needed_for_filters(
    main_model: type[Any],
    main_table: str,
    filters: list[Any],
    extra_refs: list[BoundColumnRef] | None = None,
) -> list[JoinExpression]:
    """
    For filters (and optionally extra refs from aggregates) that reference a related
    model (BoundColumnRef with model != main_model), build the required JOINs.
    """
    from pgstorm.models import BaseModel

    refs: list[BoundColumnRef] = []
    for f in filters:
        refs.extend(_collect_bound_column_refs(f))
    if extra_refs:
        refs.extend(extra_refs)

    needed: dict[type[Any], tuple[str, str]] = {}  # target_model -> (relation_attr, fk_field)
    for ref in refs:
        if ref.model is not main_model and isinstance(ref.model, type) and issubclass(ref.model, BaseModel):
            if ref.model not in needed:
                rel = _find_relation_to_model(main_model, ref.model)
                if rel is not None:
                    needed[ref.model] = rel

    result: list[JoinExpression] = []
    for target_model, (relation_attr, fk_field) in needed.items():
        rhs_table = _table_name(target_model)
        # ON: main_table.relation_attr = rhs_table.fk_field
        left_col = getattr(main_model, relation_attr)
        right_col = getattr(target_model, fk_field)
        if not isinstance(left_col, BoundColumnRef):
            left_col = left_col.__get__(None, main_model)  # get BoundColumnRef
        if not isinstance(right_col, BoundColumnRef):
            right_col = right_col.__get__(None, target_model)
        on_expr = Expression(left_col, op.EQ, right_col)
        result.append(
            JoinExpression(main_table, rhs_table, on_expr, "LEFT", rhs_model=target_model)
        )
    return result


def _compile_subquery_sql(
    qs: "QuerySet[Any]",
    params: List[Any],
    *,
    outer_table: str,
    outer_model: type[Any],
) -> sql.Composable:
    """
    Compile a queryset as a subquery (SELECT ... FROM ... WHERE ...).
    Appends params to the given list. Pass outer_table/outer_model so OuterRef
    in the subquery's filters resolves to the parent query's columns.
    """
    model = qs.model
    table = _table_name(model)
    schema = getattr(qs, "_schema", None)

    select_list = _select_list_for_queryset(qs, params)

    existing_rhs = {j.rhs_model for j in qs._joins if getattr(j, "rhs_model", None) is not None}
    agg_refs: list[BoundColumnRef] = []
    for agg, _ in getattr(qs, "_aggregates", []) or []:
        if agg.column is not None:
            agg_refs.extend(_collect_bound_column_refs(agg.column))
    auto_joins = _joins_needed_for_filters(model, table, qs._filters, extra_refs=agg_refs)
    joins_to_use = list(qs._joins)
    for j in auto_joins:
        if j.rhs_model is not None and j.rhs_model not in existing_rhs:
            joins_to_use.append(j)
            existing_rhs.add(j.rhs_model)

    parts: list[sql.Composable] = []
    parts.append(sql.SQL("SELECT "))
    if qs._distinct:
        parts.append(sql.SQL("DISTINCT "))
    parts.append(select_list)
    parts.append(sql.SQL(" FROM "))
    if schema:
        parts.append(sql.Identifier(schema, table))
    else:
        parts.append(sql.Identifier(table))

    for join in joins_to_use:
        parts.append(sql.SQL(f" {join.join_type} JOIN "))
        if getattr(join, "rhs_schema", None):
            parts.append(sql.Identifier(join.rhs_schema, join.rhs))
        else:
            parts.append(sql.Identifier(join.rhs))
        parts.append(sql.SQL(" ON "))
        on_resolver = _build_table_for_column(model, table, join.rhs_model, join.rhs)
        parts.append(
            _compile_expression(
                join.on,
                table,
                params,
                table_for_column=on_resolver,
                model=model,
                rhs_model=join.rhs_model,
            )
        )

    if qs._filters:
        where_fragments = []
        for f in qs._filters:
            frag = _compile_expression(
                f, table, params, model=model,
                outer_table=outer_table, outer_model=outer_model,
            )
            if isinstance(f, OrExpression):
                frag = sql.SQL("(") + frag + sql.SQL(")")
            where_fragments.append(frag)
        where_sql = sql.SQL(" AND ").join(where_fragments)
        parts.append(sql.SQL(" WHERE ") + where_sql)

    group_by_sql = _compile_group_by_clause(qs, table, model)
    if group_by_sql is not None:
        parts.append(group_by_sql)

    having_filters = getattr(qs, "_having", None)
    if having_filters:
        having_fragments: list[sql.Composable] = []
        for h in having_filters:
            frag = _compile_expression(h, table, params, model=model)
            if isinstance(h, OrExpression):
                frag = sql.SQL("(") + frag + sql.SQL(")")
            having_fragments.append(frag)
        parts.append(sql.SQL(" HAVING ") + sql.SQL(" AND ").join(having_fragments))

    if qs._order_by:
        order_parts = []
        for ob in qs._order_by:
            if isinstance(ob, Expression):
                lhs = ob.lhs
                direction = ob.operator.upper() if ob.operator else ""
            else:
                lhs = ob
                direction = ""
            if isinstance(lhs, BoundColumnRef):
                order_table = _table_name(lhs.model)
                col_name = _db_column_name(lhs, lhs.model)
            elif isinstance(lhs, Column):
                col_name = _db_column_name(lhs, model, None)
                order_table = table
            else:
                col_name = _db_column_name(lhs, model, None) or getattr(lhs, "name", str(lhs))
                order_table = table
            col_ident = sql.Identifier(order_table, col_name)
            if direction in ("ASC", "DESC"):
                order_parts.append(col_ident + sql.SQL(f" {direction}"))
            else:
                order_parts.append(col_ident)
        if order_parts:
            parts.append(sql.SQL(" ORDER BY ") + sql.SQL(", ").join(order_parts))

    if qs._limit:
        parts.append(sql.SQL(" LIMIT ") + sql.Placeholder())
        params.append(int(qs._limit))
    if qs._offset:
        parts.append(sql.SQL(" OFFSET ") + sql.Placeholder())
        params.append(int(qs._offset))

    return sql.Composed(parts)


def _build_table_for_column(
    main_model: type[Any], main_table: str, rhs_model: type[Any] | None, rhs_table: str
) -> Callable[[Any], str]:
    """Build a callable that maps a Column to its table name (for JOIN ON clauses)."""

    def table_for_column(column: Any) -> str:
        from pgstorm.columns.base import Field

        for _attr, attr_value in vars(main_model).items():
            if isinstance(attr_value, Field):
                col = attr_value.get_column()
                if col is not None and col is column:
                    return main_table
        if rhs_model is not None:
            for _attr, attr_value in vars(rhs_model).items():
                if isinstance(attr_value, Field):
                    col = attr_value.get_column()
                    if col is not None and col is column:
                        return rhs_table
        return main_table

    return table_for_column


def _compile_subquery_sql(
    qs: "QuerySet[Any]",
    params: List[Any],
    *,
    outer_table: str,
    outer_model: type[Any],
) -> sql.Composable:
    """
    Compile a queryset as a subquery (SELECT ... FROM ... WHERE ...).
    Used when Subquery is RHS in an expression. Pass outer_table/outer_model
    so OuterRef in the subquery's filters resolves to the parent's table.
    """
    model = qs.model
    table = _table_name(model)
    schema = getattr(qs, "_schema", None)

    select_list = _select_list_for_queryset(qs, params)

    existing_rhs = {j.rhs_model for j in qs._joins if getattr(j, "rhs_model", None) is not None}
    agg_refs: list[BoundColumnRef] = []
    for agg, _ in getattr(qs, "_aggregates", []) or []:
        if agg.column is not None:
            agg_refs.extend(_collect_bound_column_refs(agg.column))
    auto_joins = _joins_needed_for_filters(model, table, qs._filters, extra_refs=agg_refs)
    joins_to_use = list(qs._joins)
    for j in auto_joins:
        if j.rhs_model is not None and j.rhs_model not in existing_rhs:
            joins_to_use.append(j)
            existing_rhs.add(j.rhs_model)

    parts: list[sql.Composable] = []
    parts.append(sql.SQL("SELECT "))
    if qs._distinct:
        parts.append(sql.SQL("DISTINCT "))
    parts.append(select_list)
    parts.append(sql.SQL(" FROM "))
    if schema:
        parts.append(sql.Identifier(schema, table))
    else:
        parts.append(sql.Identifier(table))

    for join in joins_to_use:
        parts.append(sql.SQL(f" {join.join_type} JOIN "))
        if getattr(join, "rhs_schema", None):
            parts.append(sql.Identifier(join.rhs_schema, join.rhs))
        else:
            parts.append(sql.Identifier(join.rhs))
        parts.append(sql.SQL(" ON "))
        on_resolver = _build_table_for_column(model, table, join.rhs_model, join.rhs)
        parts.append(
            _compile_expression(
                join.on,
                table,
                params,
                table_for_column=on_resolver,
                model=model,
                rhs_model=join.rhs_model,
            )
        )

    if qs._filters:
        where_fragments = []
        for f in qs._filters:
            frag = _compile_expression(
                f, table, params, model=model,
                outer_table=outer_table, outer_model=outer_model,
            )
            if isinstance(f, OrExpression):
                frag = sql.SQL("(") + frag + sql.SQL(")")
            where_fragments.append(frag)
        parts.append(sql.SQL(" WHERE ") + sql.SQL(" AND ").join(where_fragments))

    group_by_sql = _compile_group_by_clause(qs, table, model)
    if group_by_sql is not None:
        parts.append(group_by_sql)

    having_filters = getattr(qs, "_having", None)
    if having_filters:
        having_fragments: list[sql.Composable] = []
        for h in having_filters:
            frag = _compile_expression(h, table, params, model=model)
            if isinstance(h, OrExpression):
                frag = sql.SQL("(") + frag + sql.SQL(")")
            having_fragments.append(frag)
        parts.append(sql.SQL(" HAVING ") + sql.SQL(" AND ").join(having_fragments))

    if qs._order_by:
        order_parts = []
        for ob in qs._order_by:
            if isinstance(ob, Expression):
                lhs = ob.lhs
                direction = ob.operator.upper() if ob.operator else ""
            else:
                lhs = ob
                direction = ""
            if isinstance(lhs, BoundColumnRef):
                order_table = _table_name(lhs.model)
                col_name = _db_column_name(lhs, lhs.model)
            elif isinstance(lhs, Column):
                col_name = _db_column_name(lhs, model, None)
                order_table = table
            else:
                col_name = _db_column_name(lhs, model, None) or getattr(lhs, "name", str(lhs))
                order_table = table
            col_ident = sql.Identifier(order_table, col_name)
            if direction in ("ASC", "DESC"):
                order_parts.append(col_ident + sql.SQL(f" {direction}"))
            else:
                order_parts.append(col_ident)
        if order_parts:
            parts.append(sql.SQL(" ORDER BY ") + sql.SQL(", ").join(order_parts))

    if qs._limit:
        parts.append(sql.SQL(" LIMIT ") + sql.Placeholder())
        params.append(int(qs._limit))
    if qs._offset:
        parts.append(sql.SQL(" OFFSET ") + sql.Placeholder())
        params.append(int(qs._offset))

    return sql.Composed(parts)


def _is_view_model(model: type[Any]) -> bool:
    """Return True if model is a view (has __queryset__ or __query__)."""
    from pgstorm.views import BaseView
    return (
        isinstance(model, type)
        and issubclass(model, BaseView)
        and (getattr(model, "__queryset__", None) is not None or getattr(model, "__query__", None) is not None)
    )


def _build_view_subquery(model: type[Any], params: List[Any], schema: str | None) -> tuple[sql.Composable, List[Any]]:
    """
    Build the subquery SQL for a view model from __queryset__ or __query__.
    Returns (sql_composable, subquery_params).
    """
    from pgstorm.queryset.base import QuerySet

    sub_params: List[Any] = []
    queryset_def = getattr(model, "__queryset__", None)
    query_def = getattr(model, "__query__", None)

    if queryset_def is not None:
        sub_qs = queryset_def() if callable(queryset_def) else queryset_def
        if not isinstance(sub_qs, QuerySet):
            raise TypeError(f"{model.__name__}.__queryset__ must be a QuerySet or callable returning QuerySet")
        # Apply schema: query-level using_schema() overrides view-level __schema__
        effective_schema = schema or getattr(model, "__schema__", None)
        if effective_schema is not None:
            sub_qs = sub_qs.using_schema(effective_schema)
        sub_compiled = compile_queryset(sub_qs)
        sub_params.extend(sub_compiled.params)
        sub_sql = sub_compiled.sql
    elif query_def is not None:
        # __query__: raw SQL string, or (sql_string, params) for parameterized
        effective_schema = schema or getattr(model, "__schema__", None)
        if isinstance(query_def, tuple):
            raw_sql = query_def[0]
            sub_params.extend(query_def[1])
        else:
            raw_sql = query_def
        # Substitute {schema} placeholder with properly-quoted schema identifier
        if effective_schema is not None and "{schema}" in raw_sql:
            schema_quoted = '"' + effective_schema.replace('"', '""') + '"'
            raw_sql = raw_sql.replace("{schema}", schema_quoted)
        sub_sql = sql.SQL(raw_sql)
    else:
        raise ValueError(f"{model.__name__} must define __queryset__ or __query__")

    return sub_sql, sub_params


def compile_queryset(qs: "QuerySet[Any]") -> CompiledQuery:
    """
    Compile a QuerySet into a parameterised SELECT statement.

    This understands:
      - filters (AND-combined, including NotExpression, AndExpression)
      - distinct()
      - order_by()
      - limit()
      - offset()
      - defer()/explicit column selection when available on the model
      - joins (LEFT/RIGHT/INNER/FULL/LATERAL)
      - view models (BaseView with __queryset__ or __query__) as subquery/CTE
    """

    model = qs.model
    table = _table_name(model)
    schema = getattr(qs, "_schema", None)

    query_parts: list[sql.Composable] = []
    params: list[Any] = []
    select_list = _select_list_for_queryset(qs, params)

    # Auto-add JOINs when filters or aggregates reference related model columns
    existing_rhs = {j.rhs_model for j in qs._joins if getattr(j, "rhs_model", None) is not None}
    agg_refs: list[BoundColumnRef] = []
    for agg, _ in getattr(qs, "_aggregates", []) or []:
        if agg.column is not None:
            agg_refs.extend(_collect_bound_column_refs(agg.column))
    auto_joins = _joins_needed_for_filters(model, table, qs._filters, extra_refs=agg_refs)
    joins_to_use = list(qs._joins)
    for j in auto_joins:
        if j.rhs_model is not None and j.rhs_model not in existing_rhs:
            joins_to_use.append(j)
            existing_rhs.add(j.rhs_model)

    # Build FROM clause: table or (subquery) AS alias
    is_view = _is_view_model(model)
    is_cte = is_view and getattr(model, "__is_cte__", False)

    if is_view:
        sub_sql, sub_params = _build_view_subquery(model, params, schema)
        if is_cte:
            from_clause = sql.Identifier(table)
        else:
            params.extend(sub_params)
            from_clause = sql.SQL("(") + sub_sql + sql.SQL(") AS ") + sql.Identifier(table)
    else:
        from_clause = sql.Identifier(schema, table) if schema else sql.Identifier(table)

    # SELECT [DISTINCT] <columns> FROM <table|subquery>
    if is_cte:
        # WITH cte_name AS (subquery) SELECT ... FROM cte_name
        query_parts.insert(0, sql.SQL("WITH ") + sql.Identifier(table) + sql.SQL(" AS (") + sub_sql + sql.SQL(") "))
    query_parts.append(sql.SQL("SELECT "))
    if qs._distinct:
        query_parts.append(sql.SQL("DISTINCT "))
    query_parts.append(select_list)
    query_parts.append(sql.SQL(" FROM "))
    query_parts.append(from_clause)

    # JOINs
    for join in joins_to_use:
        query_parts.append(sql.SQL(f" {join.join_type} JOIN "))
        if getattr(join, "rhs_schema", None):
            query_parts.append(sql.Identifier(join.rhs_schema, join.rhs))
        else:
            query_parts.append(sql.Identifier(join.rhs))
        query_parts.append(sql.SQL(" ON "))
        on_resolver = _build_table_for_column(
            model, table, join.rhs_model, join.rhs
        )
        query_parts.append(
            _compile_expression(
                join.on,
                table,
                params,
                table_for_column=on_resolver,
                model=model,
                rhs_model=join.rhs_model,
            )
        )

    # WHERE ...
    if qs._filters:
        where_fragments: list[sql.Composable] = []
        ann = getattr(qs, "_annotations", {}) or {}
        al = getattr(qs, "_aliases", {}) or {}
        for f in qs._filters:
            frag = _compile_expression(
                f, table, params, model=model,
                annotations=ann, aliases=al,
            )
            # Wrap OR in parens so (a OR b) AND c has correct precedence
            if isinstance(f, OrExpression):
                frag = sql.SQL("(") + frag + sql.SQL(")")
            where_fragments.append(frag)

        where_sql = sql.SQL(" AND ").join(where_fragments)
        query_parts.append(sql.SQL(" WHERE ") + where_sql)

    # GROUP BY ...
    group_by_sql = _compile_group_by_clause(qs, table, model)
    if group_by_sql is not None:
        query_parts.append(group_by_sql)

    # HAVING ...
    having_filters = getattr(qs, "_having", None)
    if having_filters:
        having_fragments: list[sql.Composable] = []
        ann = getattr(qs, "_annotations", {}) or {}
        al = getattr(qs, "_aliases", {}) or {}
        agg_aliases: dict[str, Aggregate] = {}
        for agg, alias in getattr(qs, "_aggregates", []) or []:
            agg_aliases[alias] = agg
        for h in having_filters:
            frag = _compile_expression(
                h, table, params, model=model,
                annotations=ann, aliases=al,
            )
            if isinstance(h, OrExpression):
                frag = sql.SQL("(") + frag + sql.SQL(")")
            having_fragments.append(frag)
        having_sql = sql.SQL(" AND ").join(having_fragments)
        query_parts.append(sql.SQL(" HAVING ") + having_sql)

    # ORDER BY ...
    if qs._order_by:
        order_parts: list[sql.Composable] = []
        for ob in qs._order_by:
            if isinstance(ob, Expression):
                lhs = ob.lhs
                direction = ob.operator.upper() if ob.operator else ""
            else:
                lhs = ob
                direction = ""

            if isinstance(lhs, BoundColumnRef):
                order_table = _table_name(lhs.model)
                col_name = _db_column_name(lhs, lhs.model)
            elif isinstance(lhs, Column):
                col_name = _db_column_name(lhs, model, None)
                order_table = table
            else:
                col_name = _db_column_name(lhs, model, None) or getattr(lhs, "name", str(lhs))
                order_table = table

            col_ident = sql.Identifier(order_table, col_name)
            if direction in ("ASC", "DESC"):
                order_parts.append(col_ident + sql.SQL(f" {direction}"))
            else:
                order_parts.append(col_ident)

        if order_parts:
            order_sql = sql.SQL(", ").join(order_parts)
            query_parts.append(sql.SQL(" ORDER BY ") + order_sql)

    # LIMIT / OFFSET
    if qs._limit:
        query_parts.append(sql.SQL(" LIMIT ") + sql.Placeholder())
        params.append(int(qs._limit))

    if qs._offset:
        query_parts.append(sql.SQL(" OFFSET ") + sql.Placeholder())
        params.append(int(qs._offset))

    # For CTE: subquery params must come first (in WITH clause)
    if is_view and is_cte:
        params = sub_params + params

    query = sql.Composed(query_parts)
    return CompiledQuery(
        sql=query, params=params, action="fetch", model=model, table=table
    )


# --- DML: INSERT, UPDATE, DELETE ---


def _instance_to_row_data(
    instance: Any,
    model: type[Any],
    *,
    include_pk: bool = True,
    columns: list[tuple[str, Column]] | None = None,
) -> dict[str, Any]:
    """
    Extract {db_column_name: value} from a model instance.
    For RelationField, resolves related object to its PK value.
    """
    from pgstorm.models import BaseModel

    if columns is None:
        columns = list(_iter_model_columns(model))

    result: dict[str, Any] = {}
    pk_attr = _model_primary_key_field(model)

    for attr_name, col in columns:
        db_name = (col.name if getattr(col, "name", None) else None) or attr_name
        if not include_pk and attr_name == pk_attr:
            continue

        raw = getattr(instance, f"_pgstorm_value_{attr_name}", None)
        if not hasattr(instance, f"_pgstorm_value_{attr_name}"):
            raw = getattr(instance, attr_name, None)

        # Use column default when raw is None (e.g. created_at with default=Now())
        if raw is None and col is not None and getattr(col, "default", None) is not None:
            raw = col.default

        # Pass through expression types (Subquery, Func, Expression, etc.) - do not resolve
        if _is_expression_value(raw):
            result[db_name] = raw
            continue

        # FK/OneToOne: resolve related object to its PK value
        fd = getattr(model, attr_name, None)
        if isinstance(fd, RelationField) and raw is not None:
            target = getattr(fd, "_target_model", None)
            fk_pk = _model_primary_key_field(target) if target else "id"
            raw = getattr(raw, fk_pk, None)

        result[db_name] = raw

    return result


def _apply_row_to_instance(instance: Any, row: dict[str, Any], model: type[Any]) -> None:
    """
    Apply a row dict (db_column -> value) to an existing instance.
    Maps db column names to attribute names and sets values via descriptors.
    """
    attr_names = {attr for attr, _ in _iter_model_columns(model)}
    db_col_to_attr: dict[str, str] = {}
    for attr_name, col in _iter_model_columns(model):
        if col and getattr(col, "name", None) and col.name != attr_name:
            db_col_to_attr[col.name] = attr_name

    for key, value in row.items():
        attr = db_col_to_attr.get(key, key)
        if attr in attr_names:
            setattr(instance, attr, value)


def compile_insert(
    model: type[Any],
    rows_data: list[dict[str, Any]],
    schema: str | None = None,
    *,
    returning: bool = True,
    extra: dict[str, Any] | None = None,
) -> CompiledQuery:
    """
    Compile INSERT for one or more rows.
    rows_data: list of {db_column_name: value}.
    If returning=True, adds RETURNING * to get generated values (e.g. id).
    """
    if not rows_data:
        raise ValueError("rows_data cannot be empty")
    table = _table_name(model)
    params: list[Any] = []
    cols = sorted(rows_data[0].keys())
    col_idents = [sql.Identifier(c) for c in cols]

    value_rows: list[sql.Composable] = []
    for row in rows_data:
        value_parts: list[sql.Composable] = []
        for c in cols:
            val = row.get(c)
            if _is_expression_value(val):
                value_parts.append(_compile_dml_value(val, table, params, model))
            else:
                params.append(val)
                value_parts.append(sql.Placeholder())
        value_rows.append(sql.SQL("(") + sql.SQL(", ").join(value_parts) + sql.SQL(")"))

    target = sql.Identifier(schema, table) if schema else sql.Identifier(table)
    query = (
        sql.SQL("INSERT INTO ")
        + target
        + sql.SQL(" (")
        + sql.SQL(", ").join(col_idents)
        + sql.SQL(") VALUES ")
        + sql.SQL(", ").join(value_rows)
    )
    if returning:
        query = query + sql.SQL(" RETURNING *")
    action = "bulk_create" if len(rows_data) > 1 else "create"
    return CompiledQuery(
        sql=query,
        params=params,
        action=action,
        model=model,
        table=table,
        extra=extra,
    )


def compile_update_one(
    model: type[Any],
    row_data: dict[str, Any],
    pk_value: Any,
    schema: str | None = None,
    *,
    returning: bool = True,
    extra: dict[str, Any] | None = None,
) -> CompiledQuery:
    """Compile UPDATE for a single row by primary key. If returning=True, adds RETURNING *."""
    table = _table_name(model)
    pk_attr = _model_primary_key_field(model)
    all_cols = dict(_iter_model_columns(model))
    db_pk = None
    for an, col in all_cols.items():
        if an == pk_attr:
            db_pk = (col.name if getattr(col, "name", None) else None) or an
            break
    if not db_pk:
        db_pk = "id"

    # Exclude pk from SET
    set_data = {k: v for k, v in row_data.items() if k != db_pk}
    if not set_data:
        raise ValueError("No columns to update")

    params: list[Any] = []
    set_parts: list[sql.Composable] = []
    for k in sorted(set_data.keys()):
        val = set_data[k]
        if _is_expression_value(val):
            set_parts.append(
                sql.Identifier(k) + sql.SQL(" = ") + _compile_dml_value(val, table, params, model)
            )
        else:
            set_parts.append(sql.Identifier(k) + sql.SQL(" = ") + sql.Placeholder())
            params.append(val)
    params.append(pk_value)

    target = sql.Identifier(schema, table) if schema else sql.Identifier(table)
    query = (
        sql.SQL("UPDATE ")
        + target
        + sql.SQL(" SET ")
        + sql.SQL(", ").join(set_parts)
        + sql.SQL(" WHERE ")
        + sql.Identifier(db_pk)
        + sql.SQL(" = ")
        + sql.Placeholder()
    )
    if returning:
        query = query + sql.SQL(" RETURNING *")
    return CompiledQuery(
        sql=query,
        params=params,
        action="update",
        model=model,
        table=table,
        extra=extra,
    )


def compile_bulk_update(
    model: type[Any],
    rows_data: list[dict[str, Any]],
    fields: list[str],
    schema: str | None = None,
    *,
    extra: dict[str, Any] | None = None,
) -> CompiledQuery:
    """
    Compile bulk UPDATE using CASE WHEN for efficiency.
    rows_data: list of {db_column_name: value}, each must include the pk.
    fields: db column names to update (excluding pk).
    """
    if not rows_data or not fields:
        raise ValueError("rows_data and fields cannot be empty")
    table = _table_name(model)
    pk_attr = _model_primary_key_field(model)
    all_cols = dict(_iter_model_columns(model))
    db_pk = None
    for an, col in all_cols.items():
        if an == pk_attr:
            db_pk = (col.name if getattr(col, "name", None) else None) or an
            break
    if not db_pk:
        db_pk = "id"

    params: list[Any] = []
    set_parts: list[sql.Composable] = []
    for field in fields:
        if field == db_pk:
            continue
        when_clauses: list[sql.Composable] = []
        for row in rows_data:
            pk_val = row.get(db_pk)
            if pk_val is None:
                raise ValueError(f"Row missing primary key {db_pk}")
            val = row.get(field)
            if _is_expression_value(val):
                when_clauses.append(
                    sql.SQL(" WHEN ") + sql.Placeholder() + sql.SQL(" THEN ") + _compile_dml_value(val, table, params, model)
                )
            else:
                when_clauses.append(sql.SQL(" WHEN ") + sql.Placeholder() + sql.SQL(" THEN ") + sql.Placeholder())
                params.append(val)
            params.append(pk_val)
        set_parts.append(
            sql.Identifier(field)
            + sql.SQL(" = (CASE ")
            + sql.Identifier(db_pk)
            + sql.SQL(" ").join(when_clauses)
            + sql.SQL(" END)")
        )

    in_placeholders = sql.SQL(", ").join([sql.Placeholder() for _ in rows_data])
    for row in rows_data:
        params.append(row[db_pk])

    target = sql.Identifier(schema, table) if schema else sql.Identifier(table)
    query = (
        sql.SQL("UPDATE ")
        + target
        + sql.SQL(" SET ")
        + sql.SQL(", ").join(set_parts)
        + sql.SQL(" WHERE ")
        + sql.Identifier(db_pk)
        + sql.SQL(" IN (")
        + in_placeholders
        + sql.SQL(")")
    )
    return CompiledQuery(
        sql=query,
        params=params,
        action="bulk_update",
        model=model,
        table=table,
        extra=extra,
    )


def compile_delete_by_pk(model: type[Any], pk_value: Any, schema: str | None = None) -> CompiledQuery:
    """Compile DELETE for a single row by primary key."""
    table = _table_name(model)
    pk_attr = _model_primary_key_field(model)
    all_cols = dict(_iter_model_columns(model))
    db_pk = None
    for an, col in all_cols.items():
        if an == pk_attr:
            db_pk = (col.name if getattr(col, "name", None) else None) or an
            break
    if not db_pk:
        db_pk = "id"

    params: list[Any] = [pk_value]
    target = sql.Identifier(schema, table) if schema else sql.Identifier(table)
    query = (
        sql.SQL("DELETE FROM ")
        + target
        + sql.SQL(" WHERE ")
        + sql.Identifier(db_pk)
        + sql.SQL(" = ")
        + sql.Placeholder()
    )
    return CompiledQuery(
        sql=query, params=params, action="delete", model=model, table=table
    )


def compile_delete_queryset(qs: "QuerySet[Any]") -> CompiledQuery:
    """
    Compile DELETE for a queryset. Uses subquery when filters reference joins.
    """
    model = qs.model
    table = _table_name(model)
    schema = getattr(qs, "_schema", None)
    pk_attr = _model_primary_key_field(model)
    all_cols = dict(_iter_model_columns(model))
    db_pk = None
    for an, col in all_cols.items():
        if an == pk_attr:
            db_pk = (col.name if getattr(col, "name", None) else None) or an
            break
    if not db_pk:
        db_pk = "id"

    # If we have joins, use subquery: DELETE FROM t WHERE pk IN (SELECT pk FROM t JOIN ... WHERE ...)
    has_joins = bool(getattr(qs, "_joins", None))
    if has_joins:
        from pgstorm.queryset.base import QuerySet

        sub_qs = QuerySet(model)
        sub_qs._schema = schema
        sub_qs._filters = list(qs._filters)
        sub_qs._joins = list(qs._joins)
        sub_qs._columns = [pk_attr]
        sub_compiled = compile_queryset(sub_qs)
        # Build DELETE FROM t WHERE pk IN (subquery)
        target = sql.Identifier(schema, table) if schema else sql.Identifier(table)
        # The subquery returns rows with one column (pk). We need WHERE pk IN (SELECT ...)
        # compile_queryset produces SELECT table.pk FROM ... - the column might be aliased
        # Simpler: use the raw subquery sql and params
        params = list(sub_compiled.params)
        query = (
            sql.SQL("DELETE FROM ")
            + target
            + sql.SQL(" WHERE ")
            + sql.Identifier(db_pk)
            + sql.SQL(" IN (")
            + sub_compiled.sql
            + sql.SQL(")")
        )
        return CompiledQuery(
            sql=query, params=params, action="delete", model=model, table=table
        )

    # No joins: simple DELETE FROM t WHERE ...
    params: list[Any] = []
    target = sql.Identifier(schema, table) if schema else sql.Identifier(table)
    query_parts: list[sql.Composable] = [
        sql.SQL("DELETE FROM "),
        target,
    ]
    if qs._filters:
        ann = getattr(qs, "_annotations", {}) or {}
        al = getattr(qs, "_aliases", {}) or {}
        where_fragments = []
        for f in qs._filters:
            frag = _compile_expression(f, table, params, model=model, annotations=ann, aliases=al)
            if isinstance(f, OrExpression):
                frag = sql.SQL("(") + frag + sql.SQL(")")
            where_fragments.append(frag)
        query_parts.append(sql.SQL(" WHERE ") + sql.SQL(" AND ").join(where_fragments))
    query = sql.Composed(query_parts)
    return CompiledQuery(
        sql=query, params=params, action="delete", model=model, table=table
    )


def compile_queryset_update(qs: "QuerySet[Any]", updates: dict[str, Any]) -> CompiledQuery:
    """
    Compile UPDATE for a queryset with the given field updates.
    updates: {attr_name: value} - values can be literals or expressions (Subquery, Func, etc.).
    Uses subquery when filters reference joins.
    """
    model = qs.model
    table = _table_name(model)
    schema = getattr(qs, "_schema", None)
    pk_attr = _model_primary_key_field(model)
    all_cols = dict(_iter_model_columns(model))
    db_pk = None
    for an, col in all_cols.items():
        if an == pk_attr:
            db_pk = (col.name if getattr(col, "name", None) else None) or an
            break
    if not db_pk:
        db_pk = "id"

    # Resolve attr names to db column names and build SET clause
    set_parts: list[sql.Composable] = []
    params: list[Any] = []
    for attr_name, val in updates.items():
        if attr_name == pk_attr or attr_name == db_pk:
            continue
        col = all_cols.get(attr_name)
        db_name = (col.name if col and getattr(col, "name", None) else None) or attr_name
        if _is_expression_value(val):
            set_parts.append(
                sql.Identifier(db_name) + sql.SQL(" = ") + _compile_dml_value(val, table, params, model)
            )
        else:
            set_parts.append(sql.Identifier(db_name) + sql.SQL(" = ") + sql.Placeholder())
            params.append(val)

    if not set_parts:
        raise ValueError("No columns to update")

    target = sql.Identifier(schema, table) if schema else sql.Identifier(table)
    set_sql = sql.SQL(", ").join(set_parts)

    has_joins = bool(getattr(qs, "_joins", None))
    if has_joins:
        from pgstorm.queryset.base import QuerySet

        sub_qs = QuerySet(model)
        sub_qs._schema = schema
        sub_qs._filters = list(qs._filters)
        sub_qs._joins = list(qs._joins)
        sub_qs._columns = [pk_attr]
        sub_compiled = compile_queryset(sub_qs)
        params.extend(sub_compiled.params)
        query = (
            sql.SQL("UPDATE ")
            + target
            + sql.SQL(" SET ")
            + set_sql
            + sql.SQL(" WHERE ")
            + sql.Identifier(db_pk)
            + sql.SQL(" IN (")
            + sub_compiled.sql
            + sql.SQL(")")
        )
        return CompiledQuery(
            sql=query, params=params, action="update", model=model, table=table
        )

    # No joins: UPDATE table SET ... WHERE ...
    query_parts: list[sql.Composable] = [
        sql.SQL("UPDATE "),
        target,
        sql.SQL(" SET "),
        set_sql,
    ]
    if qs._filters:
        ann = getattr(qs, "_annotations", {}) or {}
        al = getattr(qs, "_aliases", {}) or {}
        where_fragments = []
        for f in qs._filters:
            frag = _compile_expression(f, table, params, model=model, annotations=ann, aliases=al)
            if isinstance(f, OrExpression):
                frag = sql.SQL("(") + frag + sql.SQL(")")
            where_fragments.append(frag)
        query_parts.append(sql.SQL(" WHERE ") + sql.SQL(" AND ").join(where_fragments))
    query = sql.Composed(query_parts)
    return CompiledQuery(
        sql=query, params=params, action="update", model=model, table=table
    )