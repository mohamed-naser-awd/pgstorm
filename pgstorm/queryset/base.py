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
        self._schema = schema
        return self

    def _fetch(self) -> list[T]:
        """Load results from the database via the engine from context."""
        from pgstorm.engine.context import engine as engine_context_var

        eng = engine_context_var.get()
        if eng is None:
            raise RuntimeError(
                "No engine set. Call create_engine() or engine.set(engine) before using querysets."
            )
        if eng.is_async:
            raise RuntimeError(
                "Cannot iterate synchronously with async engine. Use await queryset.fetch() or async for."
            )
        compiled = self.compiled()
        rows = eng.execute(compiled)
        return self._rows_to_instances(rows)

    def _rows_to_instances(self, rows: list[dict[str, Any]]) -> list[T]:
        """Map row dicts to model instances. When joins with rhs_model exist, hydrate both main and joined objects."""
        from pgstorm.columns.base import RelationField
        from pgstorm.queryset.parser import (
            _find_relation_to_model,
            _iter_model_columns,
            _table_name,
        )

        model = self.model
        attr_names = {attr for attr, _ in _iter_model_columns(model)}
        annotation_names = set(getattr(self, "_annotations", {}).keys())
        settable = attr_names | annotation_names

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

    def __getitem__(self, index: int) -> T:
        return self._ensure_fetched()[index]

    def __len__(self) -> int:
        return len(self._ensure_fetched())

    def as_cte(self, name: str = None) -> Self:
        self.is_cte = True
        self.cte_name = name
        return self

    def all(self) -> Self:
        return self

    def filter(self, *args: Expression | NotExpression | Q) -> Self:
        from pgstorm.functions.expression import _to_expression

        for arg in args:
            expr = _to_expression(arg) if isinstance(arg, Q) else arg
            self._filters.append(expr)
        return self

    def exclude(self, *args: Expression) -> Self:
        return self.filter(*(NotExpression(e) for e in args))

    def order_by(self, *args: Expression) -> Self:
        self._order_by.extend(args)
        return self

    def limit(self, limit: int) -> Self:
        self._limit = limit
        return self

    def offset(self, offset: int) -> Self:
        self._offset = offset
        return self

    def defer(self, *args: str) -> Self:
        self._exclude_columns.extend(args)
        return self

    def columns(self, *args: str) -> Self:
        self._columns.extend(args)
        return self

    def aggregate(
        self,
        *args: "Aggregate",
        **kwargs: "Aggregate",
    ) -> Self:
        """
        Add aggregate functions to the SELECT clause.

        - Positional args: alias = col_name_function_name (e.g. Min(User.age) -> age_min)
        - Keyword args: alias = key (e.g. total=Sum(User.price) -> total)
        """
        from pgstorm.functions.aggregate import Aggregate, _default_alias_for_aggregate

        for agg in args:
            if not isinstance(agg, Aggregate):
                raise TypeError(f"Expected Aggregate, got {type(agg).__name__}")
            alias = _default_alias_for_aggregate(agg)
            self._aggregates.append((agg, alias))
        for key, agg in kwargs.items():
            if not isinstance(agg, Aggregate):
                raise TypeError(f"Expected Aggregate, got {type(agg).__name__}")
            self._aggregates.append((agg, key))
        return self

    def annotate(self, **kwargs: Any) -> Self:
        """
        Add computed expressions to the SELECT clause. Results include these values.
        Example: Model.objects.annotate(full_name=Concat(User.first_name, " ", User.last_name))
        """
        self._annotations.update(kwargs)
        return self

    def alias(self, **kwargs: Any) -> Self:
        """
        Define expressions for use in filter/order_by without including in SELECT.
        Example: Model.objects.alias(foo=Concat(...)).filter(F("foo").ilike("%x%"))
        -> WHERE CONCAT(...) ILIKE '%x%'
        """
        self._aliases.update(kwargs)
        return self

    def distinct(self, *args: str) -> Self:
        self._distinct = True
        return self

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

        qs = self.aggregate(count=Count())
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

        lhs_table = _table_name(self.model)
        if isinstance(join_with, type) and issubclass(join_with, BaseModel):
            rhs_table = _table_name(join_with)
        else:
            raise TypeError("join_with must be a model class")
        # If no explicit rhs_schema is provided, default to this queryset's schema.
        effective_rhs_schema = rhs_schema if rhs_schema is not None else self._schema
        self._joins.append(
            JoinExpression(
                lhs_table,
                rhs_table,
                on,
                join_type,
                rhs_model=join_with,
                lhs_schema=self._schema,
                rhs_schema=effective_rhs_schema,
            )
        )
        return self
