from __future__ import annotations

from pgstorm.functions.expression import (
    Expression,
    NotExpression,
    JoinExpression,
    Q,
)
from typing import (
    Any,
    Awaitable,
    Self,
    Generic,
    TypeVar,
    TYPE_CHECKING,
    Literal,
    Iterator,
    AsyncIterator,
    overload,
)
from psycopg.sql import Composable

from pgstorm.models import BaseModel

if TYPE_CHECKING:
    from pgstorm.queryset.parser import CompiledQuery

T = TypeVar("T", bound=BaseModel)


class QuerySetWrapper(Generic[T]):
    """Descriptor that returns a QuerySet bound to the model class. Enables Model.objects.all() typing."""

    def __get__(self, obj: object, owner: type[T] | None = None) -> QuerySet[T]:
        if owner is None:
            raise AttributeError("QuerySetDescriptor must be accessed on a model class")
        return QuerySet(owner)


class QuerySetMagicMethodsMixin:
    """
    Add magic methods to the QuerySet class.
    """


class QuerySet(Generic[T]):
    model: type[T]
    _schema: str | None
    _filters: list[Expression | NotExpression | "AndExpression" | "OrExpression"]
    _order_by: list[Expression]
    _limit: int
    _offset: int
    _columns: list[str]
    _aggregates: list[tuple[Any, str]]  # (Aggregate, alias)
    _annotations: dict[str, Any]  # alias -> expression (Func, Aggregate, etc.)
    _aliases: dict[str, Any]  # alias -> expression (for filter/order, not in SELECT)
    _distinct: bool
    _exclude_columns: list[str]
    _joins: list[JoinExpression]
    _group_by: list[Any]
    _having: list[Expression | NotExpression | "AndExpression" | "OrExpression"]
    is_cte: bool
    is_subquery: bool
    cte_name: str | None
    _result_cache: list[T] | None

    def __init__(self, model: type[T]) -> None:
        self.model = model
        self._schema = None
        self._filters = []
        self._order_by = []
        self._limit = 0
        self._offset = 0
        self._distinct = False
        self._exclude_columns = []
        self._columns = []
        self._aggregates = []
        self._annotations = {}
        self._aliases = {}
        self._joins = []
        self._group_by = []
        self._having = []
        self.is_cte = False
        self.is_subquery = False
        self.cte_name = None
        self._result_cache = None

    def using_schema(self, schema: str | None) -> Self:
        """
        Set the database schema to use for this queryset.

        When set, the main FROM table will be emitted as schema.table,
        and any explicit joins without an explicit rhs_schema will
        default to this same schema.
        """
        qs = self.copy()
        qs._schema = schema
        return qs

    def _fetch(self) -> list[T]:
        """Load results from the database via the engine from context."""
        from pgstorm.engine.context import engine as engine_context_var

        eng = engine_context_var.get()
        if eng is None:
            raise RuntimeError(
                "No engine set. Call create_engine() or engine.set(engine) before using querysets."
            )

        compiled = self.compiled()
        rows = eng.execute(compiled)
        return self._rows_to_instances(rows)

    def _rows_to_instances_sync(self, rows: list[dict[str, Any]]) -> list[T]:
        """Map row dicts to model instances. When joins with rhs_model exist, hydrate both main and joined objects.
        When the queryset has aggregates (with or without group_by), return raw row dicts instead of model instances."""
        if getattr(self, "_aggregates", []):
            return rows  # type: ignore[return-value]
        from pgstorm.columns.base import RelationField
        from pgstorm.queryset.parser import (
            _find_relation_to_model,
            _iter_model_columns,
            _table_name,
        )

        model = self.model
        attr_names = {attr for attr, _ in _iter_model_columns(model)}
        annotation_names = set(getattr(self, "_annotations", {}).keys())
        aggregate_aliases = {alias for _, alias in getattr(self, "_aggregates", [])}
        settable = attr_names | annotation_names | aggregate_aliases

        # Map DB column names to attr names (e.g. user_id -> user for FK)
        db_col_to_attr: dict[str, str] = {}
        for attr_name, col in _iter_model_columns(model):
            if col and getattr(col, "name", None) and col.name != attr_name:
                db_col_to_attr[col.name] = attr_name

        # Build join info: prefix -> (rhs_model, fk_attr_on_main, reverse_name)
        join_info: dict[str, tuple[type[Any], str, str | None]] = {}
        for join in getattr(self, "_joins", []) or []:
            rhs_model = getattr(join, "rhs_model", None)
            if rhs_model is None:
                continue
            rel = _find_relation_to_model(model, rhs_model)
            if rel is None:
                continue
            fk_attr, _ = rel
            reverse_name: str | None = None
            fd = getattr(model, fk_attr, None)
            if isinstance(fd, RelationField):
                reverse_name = getattr(fd, "_reverse_name", None)
            rhs_table = _table_name(rhs_model)
            prefix = f"{rhs_table}__"
            join_info[prefix] = (rhs_model, fk_attr, reverse_name)

        result: list[T] = []
        for row in rows:
            obj = model.__new__(model)
            joined: dict[str, Any] = {}  # prefix -> rhs instance

            for key, value in row.items():
                attr = db_col_to_attr.get(key, key)
                if attr in settable:
                    setattr(obj, attr, value)
                else:
                    for prefix, (rhs_model, fk_attr, reverse_name) in join_info.items():
                        if key.startswith(prefix):
                            attr_name = key[len(prefix) :]
                            if prefix not in joined:
                                joined[prefix] = rhs_model.__new__(rhs_model)
                            setattr(joined[prefix], attr_name, value)
                            break

            for prefix, (rhs_model, fk_attr, reverse_name) in join_info.items():
                if prefix in joined:
                    rhs_obj = joined[prefix]
                    setattr(obj, fk_attr, rhs_obj)
                    if reverse_name:
                        setattr(rhs_obj, f"_pgstorm_value_{reverse_name}", obj)
            result.append(obj)
        return result

    @overload
    def _rows_to_instances(self, rows: list[dict[str, Any]]) -> list[T]: ...
    @overload
    def _rows_to_instances(
        self, rows: Awaitable[list[dict[str, Any]]]
    ) -> Awaitable[list[T]]: ...
    def _rows_to_instances(
        self, rows: list[dict[str, Any]] | Awaitable[list[dict[str, Any]]]
    ) -> list[T] | Awaitable[list[T]]:
        """
        Map row dicts to model instances. Supports both sync and async:
        - rows: list -> returns list[T]
        - rows: Awaitable[list] -> returns Awaitable[list[T]] (use await)
        """
        if hasattr(rows, "__await__"):

            async def _run() -> list[T]:
                resolved = await rows
                return self._rows_to_instances_sync(resolved)

            return _run()
        return self._rows_to_instances_sync(rows)

    def _execute(self, compiled: "CompiledQuery", then: Any) -> Any:
        """
        Run engine.execute(compiled). If async engine, return a coroutine that awaits and calls then(rows).
        Otherwise call then(rows) and return. Used to unify sync/async API.
        """
        from pgstorm.engine.context import engine as engine_context_var

        eng = engine_context_var.get()
        if eng is None:
            raise RuntimeError(
                "No engine set. Call create_engine() or engine.set(engine) before using querysets."
            )
        if eng.is_async:

            async def _run() -> Any:
                rows = await eng.execute(compiled)
                return then(rows)

            return _run()
        return then(eng.execute(compiled))

    @overload
    def fetch(self: "QuerySet[T]") -> list[T]: ...
    @overload
    def fetch(self: "QuerySet[T]") -> Awaitable[list[T]]: ...
    def fetch(self) -> list[T] | Awaitable[list[T]]:
        """
        Load results. With sync engine returns list[T]. With async engine returns Awaitable[list[T]] — use await.
        """

        def then(rows: list[dict[str, Any]]) -> list[T]:
            self._result_cache = self._rows_to_instances(rows)
            return self._result_cache

        return self._execute(self.compiled(), then)

    def _ensure_fetched(self) -> list[T]:
        """
        Ensure this queryset has been evaluated (sync only).

        For async engines, synchronous evaluation isn't supported — use `await qs.fetch()` or `async for`.
        """
        if self._result_cache is None:
            self._result_cache = self._fetch()
        return self._result_cache

    def __iter__(self) -> Iterator[T]:
        return iter(self._ensure_fetched())

    async def __aiter__(self) -> AsyncIterator[T]:
        """Async iteration: async for item in queryset. Uses engine — await when async."""
        out = self._ensure_fetched()
        if hasattr(out, "__await__"):
            results = await out
        else:
            results = out
        for item in results:
            yield item

    @overload
    def __getitem__(self, index: int) -> T: ...
    @overload
    def __getitem__(self, index: int) -> Awaitable[T]: ...
    def __getitem__(self, index: int) -> T | Awaitable[T]:
        if self._result_cache is not None:
            return self._result_cache[index]
        def then(rows: list[dict[str, Any]]) -> T:
            instances = self._rows_to_instances(rows)
            self._result_cache = instances
            return instances[index]
        return self._execute(self.compiled(), then)

    @overload
    def __len__(self) -> int: ...
    @overload
    def __len__(self) -> Awaitable[int]: ...
    def __len__(self) -> int | Awaitable[int]:
        if self._result_cache is not None:
            return len(self._result_cache)
        def then(rows: list[dict[str, Any]]) -> int:
            instances = self._rows_to_instances(rows)
            self._result_cache = instances
            return len(instances)
        return self._execute(self.compiled(), then)

    def as_cte(self, name: str = None) -> Self:
        qs = self.copy()
        qs.is_cte = True
        qs.cte_name = name
        return qs

    def all(self) -> Self:
        return self.copy()

    def copy(self) -> Self:
        """Return a copy of this queryset. Modifications to the copy do not affect the original."""
        qs = type(self)(self.model)
        qs._schema = self._schema
        qs._filters = list(self._filters)
        qs._order_by = list(self._order_by)
        qs._limit = self._limit
        qs._offset = self._offset
        qs._columns = list(self._columns)
        qs._aggregates = list(self._aggregates)
        qs._annotations = dict(self._annotations)
        qs._aliases = dict(self._aliases)
        qs._distinct = self._distinct
        qs._exclude_columns = list(self._exclude_columns)
        qs._joins = list(self._joins)
        qs._group_by = list(self._group_by)
        qs._having = list(self._having)
        qs.is_cte = self.is_cte
        qs.is_subquery = self.is_subquery
        qs.cte_name = self.cte_name
        qs._result_cache = None
        return qs

    def filter(self, *args: Expression | NotExpression | Q) -> Self:
        from pgstorm.functions.expression import _to_expression

        qs = self.copy()
        for arg in args:
            expr = _to_expression(arg) if isinstance(arg, Q) else arg
            qs._filters.append(expr)
        return qs

    def exclude(self, *args: Expression) -> Self:
        return self.filter(*(NotExpression(e) for e in args))

    def order_by(self, *args: Expression) -> Self:
        qs = self.copy()
        qs._order_by.extend(args)
        return qs

    def limit(self, limit: int) -> Self:
        qs = self.copy()
        qs._limit = limit
        return qs

    def offset(self, offset: int) -> Self:
        qs = self.copy()
        qs._offset = offset
        return qs

    def defer(self, *args: str) -> Self:
        qs = self.copy()
        qs._exclude_columns.extend(args)
        return qs

    def columns(self, *args: str) -> Self:
        qs = self.copy()
        qs._columns.extend(args)
        return qs

    @overload
    def aggregate(
        self,
        *args: "Aggregate",
        having: Expression | NotExpression | Q | None = None,
        **kwargs: "Aggregate",
    ) -> dict[str, Any]: ...
    @overload
    def aggregate(
        self,
        *args: "Aggregate",
        having: Expression | NotExpression | Q | None = None,
        **kwargs: "Aggregate",
    ) -> Awaitable[dict[str, Any]]: ...
    @overload
    def aggregate(
        self,
        *args: "Aggregate",
        having: Expression | NotExpression | Q | None = None,
        **kwargs: "Aggregate",
    ) -> list[dict[str, Any]]: ...
    @overload
    def aggregate(
        self,
        *args: "Aggregate",
        having: Expression | NotExpression | Q | None = None,
        **kwargs: "Aggregate",
    ) -> Awaitable[list[dict[str, Any]]]: ...
    def aggregate(
        self,
        *args: "Aggregate",
        having: Expression | NotExpression | Q | None = None,
        **kwargs: "Aggregate",
    ) -> dict[str, Any] | list[dict[str, Any]] | Awaitable[dict[str, Any]] | Awaitable[list[dict[str, Any]]]:
        """
        Execute aggregate functions and return results immediately.

        - Without group_by: returns a single dict (e.g. {"total": 123, "count": 5})
        - With group_by: returns a list of dicts (one per group)

        Positional args get auto aliases (e.g. Min(User.age) -> age_min).
        Keyword args use the key as alias (e.g. total=Sum(User.price) -> total).

        Use having= to filter on aggregate results (e.g. having=F("total") > 100).

        With sync engine returns dict | list[dict]; with async returns Awaitable — use await.
        """
        from pgstorm.functions.aggregate import Aggregate, _default_alias_for_aggregate
        from pgstorm.functions.expression import _to_expression

        if not args and not kwargs:
            raise ValueError("aggregate() requires at least one aggregate (e.g. Count(), Sum(col))")

        qs = self.copy()
        for agg in args:
            if not isinstance(agg, Aggregate):
                raise TypeError(f"Expected Aggregate, got {type(agg).__name__}")
            alias = _default_alias_for_aggregate(agg)
            qs._aggregates.append((agg, alias))
        for key, agg in kwargs.items():
            if not isinstance(agg, Aggregate):
                raise TypeError(f"Expected Aggregate, got {type(agg).__name__}")
            qs._aggregates.append((agg, key))
        if having is not None:
            expr = _to_expression(having) if isinstance(having, Q) else having
            qs._having.append(expr)

        has_group_by = bool(getattr(qs, "_group_by", []))

        def then(rows: list[dict[str, Any]]) -> dict[str, Any] | list[dict[str, Any]]:
            if has_group_by:
                return rows
            return rows[0] if rows else {}

        return qs._execute(qs.compiled(), then)

    def group_by(self, *args: Any) -> QuerySet[dict]:
        """
        Add GROUP BY columns.

        Accepts BoundColumnRef (e.g. User.department) or raw column name strings.
        When used with aggregate(), the grouped columns are automatically included
        in the SELECT list alongside the aggregate expressions.

        Example:
            Product.objects.group_by(Product.category).aggregate(total=Sum(Product.price))
            -> SELECT "product"."category", SUM("product"."price") AS "total"
               FROM "product" GROUP BY "product"."category"
        """
        qs = self.copy()
        qs._group_by.extend(args)
        return qs

    def having(self, *args: Expression | NotExpression | Q) -> Self:
        """
        Add HAVING conditions (filters applied after GROUP BY).

        Chain with annotate(): .group_by(...).annotate(total=Sum(...)).having(F("total") > 100)
        For aggregate(), use the having= parameter: .aggregate(total=Sum(...), having=F("total") > 100)
        """
        from pgstorm.functions.expression import _to_expression

        qs = self.copy()
        for arg in args:
            expr = _to_expression(arg) if isinstance(arg, Q) else arg
            qs._having.append(expr)
        return qs

    def annotate(self, **kwargs: Any) -> Self:
        """
        Add computed expressions to the SELECT clause. Results include these values.
        Example: Model.objects.annotate(full_name=Concat(User.first_name, " ", User.last_name))
        """
        qs = self.copy()
        qs._annotations.update(kwargs)
        return qs

    def alias(self, **kwargs: Any) -> Self:
        """
        Define expressions for use in filter/order_by without including in SELECT.
        Example: Model.objects.alias(foo=Concat(...)).filter(F("foo").ilike("%x%"))
        -> WHERE CONCAT(...) ILIKE '%x%'
        """
        qs = self.copy()
        qs._aliases.update(kwargs)
        return qs

    def distinct(self, *args: str) -> Self:
        qs = self.copy()
        qs._distinct = True
        return qs

    def get(self, *filters: Expression | NotExpression) -> T:
        return self.filter(*filters).limit(1).all()[0]

    @overload
    def create(self: "QuerySet[T]", **kwargs: Any) -> T: ...
    @overload
    def create(self: "QuerySet[T]", **kwargs: Any) -> Awaitable[T]: ...
    def create(self, **kwargs: Any) -> T | Awaitable[T]:
        """
        Create and insert a single record. With sync engine returns T; with async engine returns Awaitable[T] — use await.
        """
        obj = self.model(**kwargs)
        out = self.bulk_create([obj])
        if hasattr(out, "__await__"):

            async def _first() -> T:
                objs = await out
                return objs[0]

            return _first()
        return out[0]

    @overload
    def count(self: "QuerySet[T]") -> int: ...
    @overload
    def count(self: "QuerySet[T]") -> Awaitable[int]: ...
    def count(self) -> int | Awaitable[int]:
        """Return the number of rows matching this queryset. With async engine use await."""
        from pgstorm.functions.aggregate import Count

        qs = self.copy()
        qs._aggregates.append((Count(), "count"))
        return qs._execute(qs.compiled(), lambda rows: rows[0]["count"] if rows else 0)

    @overload
    def bulk_create(
        self: "QuerySet[T]",
        objs: list[T],
        *,
        returning: bool = True,
    ) -> list[T]: ...
    @overload
    def bulk_create(
        self: "QuerySet[T]",
        objs: list[T],
        *,
        returning: bool = True,
    ) -> Awaitable[list[T]]: ...
    def bulk_create(
        self,
        objs: list[T],
        *,
        returning: bool = True,
    ) -> list[T] | Awaitable[list[T]]:
        """
        Insert multiple instances. With sync engine returns list[T]; with async returns Awaitable[list[T]] — use await.
        If returning=True (default), populates generated pk on each instance.
        """
        from pgstorm.queryset.parser import (
            _instance_to_row_data,
            _iter_model_columns,
            _model_primary_key_field,
            compile_insert,
        )

        if not objs:
            return objs

        model = self.model
        pk_attr = _model_primary_key_field(model)
        all_cols = dict(_iter_model_columns(model))
        db_pk = next(
            (col.name or an for an, col in all_cols.items() if an == pk_attr),
            pk_attr,
        )

        rows_data: list[dict[str, Any]] = []
        for obj in objs:
            row = _instance_to_row_data(obj, model, include_pk=True)
            if db_pk and row.get(db_pk) is None:
                row = {k: v for k, v in row.items() if k != db_pk}
            rows_data.append(row)

        if not rows_data:
            raise ValueError("No data to insert")

        compiled = compile_insert(
            model, rows_data, schema=self._schema, returning=returning
        )

        def then(result: list[dict[str, Any]] | None) -> list[T]:
            if returning and result and db_pk:
                for i, row in enumerate(result):
                    if i < len(objs) and db_pk in row:
                        setattr(objs[i], f"_pgstorm_value_{pk_attr}", row[db_pk])
            return objs

        return self._execute(compiled, then)

    @overload
    def bulk_update(
        self: "QuerySet[T]",
        objs: list[T],
        fields: list[str],
    ) -> None: ...
    @overload
    def bulk_update(
        self: "QuerySet[T]",
        objs: list[T],
        fields: list[str],
    ) -> Awaitable[None]: ...
    def bulk_update(
        self,
        objs: list[T],
        fields: list[str],
    ) -> None | Awaitable[None]:
        """
        Update multiple instances. With sync engine returns None; with async returns Awaitable[None] — use await.
        fields: attribute names to update (e.g. ['email', 'name']). Each object must have a non-None primary key.
        """
        from pgstorm.queryset.parser import (
            _instance_to_row_data,
            _iter_model_columns,
            _model_primary_key_field,
            compile_bulk_update,
        )

        if not objs or not fields:
            return None

        model = self.model
        all_cols = dict(_iter_model_columns(model))
        pk_attr = _model_primary_key_field(model)
        db_fields: list[str] = []
        for attr in fields:
            if attr == pk_attr:
                continue
            col = all_cols.get(attr)
            db_name = (col.name if col and getattr(col, "name", None) else None) or attr
            db_fields.append(db_name)

        if not db_fields:
            return None

        rows_data = [_instance_to_row_data(obj, model, include_pk=True) for obj in objs]
        compiled = compile_bulk_update(model, rows_data, db_fields, schema=self._schema)
        return self._execute(compiled, lambda _: None)

    @overload
    def update(self: "QuerySet[T]", **kwargs: Any) -> None: ...
    @overload
    def update(self: "QuerySet[T]", **kwargs: Any) -> Awaitable[None]: ...
    def update(self, **kwargs: Any) -> None | Awaitable[None]:
        """
        Update all rows matching this queryset's filters. With sync engine returns None; with async returns Awaitable[None] — use await.
        Use: User.objects.filter(User.age < 18).update(active=True, updated_at=Now())
        """
        from pgstorm.queryset.parser import compile_queryset_update

        if not kwargs:
            raise ValueError("update() requires at least one keyword argument")
        compiled = compile_queryset_update(self, kwargs)
        return self._execute(compiled, lambda _: None)

    @overload
    def delete(self: "QuerySet[T]") -> None: ...
    @overload
    def delete(self: "QuerySet[T]") -> Awaitable[None]: ...
    def delete(self) -> None | Awaitable[None]:
        """
        Delete all rows matching this queryset's filters. With sync engine returns None; with async returns Awaitable[None] — use await.
        Use: User.objects.filter(User.age < 18).delete()
        """
        from pgstorm.queryset.parser import compile_delete_queryset

        compiled = compile_delete_queryset(self)
        return self._execute(compiled, lambda _: None)

    def as_sql(self) -> tuple[Composable, list[object]]:
        """
        Compile this QuerySet into a parameterised SQL query suitable for psycopg3.

        Returned tuple is (query,
        params) where:
        - query is a psycopg.sql.Composable instance (e.g. sql.Composed)
        - params is the ordered list of parameter values.

        You can pass them directly to psycopg3 cursor.execute(query, params).
        """
        compiled = self.compiled()
        return compiled.sql, list(compiled.params)

    def compiled(self) -> CompiledQuery:
        """
        Compile this QuerySet to a CompiledQuery (sql + params). Useful for debugging
        and inspection without executing (e.g. qs.compiled().sql, qs.compiled().params).
        """
        from pgstorm.queryset.parser import compile_queryset

        return compile_queryset(self)

    def join(
        self,
        join_with: type[T] | Self,
        on: Expression,
        join_type: Literal["LEFT", "RIGHT", "INNER", "FULL", "LATERAL"] = "LEFT",
        rhs_schema: str | None = None,
    ) -> Self:
        from pgstorm.queryset.parser import _table_name

        qs = self.copy()
        lhs_table = _table_name(qs.model)
        if isinstance(join_with, type) and issubclass(join_with, BaseModel):
            rhs_table = _table_name(join_with)
        else:
            raise TypeError("join_with must be a model class")
        # If no explicit rhs_schema is provided, default to this queryset's schema.
        effective_rhs_schema = rhs_schema if rhs_schema is not None else qs._schema
        qs._joins.append(
            JoinExpression(
                lhs_table,
                rhs_table,
                on,
                join_type,
                rhs_model=join_with,
                lhs_schema=qs._schema,
                rhs_schema=effective_rhs_schema,
            )
        )
        return qs
