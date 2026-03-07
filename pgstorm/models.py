from __future__ import annotations

from typing import Any, Awaitable, ClassVar, Self, TYPE_CHECKING, overload

if TYPE_CHECKING:
    from pgstorm.columns.base import Field
    from pgstorm.queryset.base import QuerySet


class ModelMeta(type):
    """Metaclass for pgstorm models. Maps type annotations to Field descriptors and builds cls.fields."""

    def __new__(mcs, name: str, bases: tuple, namespace: dict[str, Any]) -> type:
        cls = super().__new__(mcs, name, bases, namespace)
        from pgstorm.columns.base import Field

        fields: dict[str, Any] = {}
        for base in reversed(cls.__mro__):
            if base is object:
                continue
            ann = getattr(base, "__annotations__", {})
            for attr_name, field_annotation in ann.items():
                if attr_name.startswith("_"):
                    continue
                if attr_name in fields:
                    continue
                if attr_name in base.__dict__:
                    val = base.__dict__[attr_name]
                    if isinstance(val, Field):
                        fields[attr_name] = val
                        continue
                descriptor = Field.generate_descriptor(field_annotation)
                if descriptor is not None:
                    setattr(cls, attr_name, descriptor)
                    if hasattr(descriptor, "__set_name__"):
                        descriptor.__set_name__(cls, attr_name)
                    fields[attr_name] = descriptor

        cls.fields = fields

        if cls.__name__ != "BaseModel" and "objects" not in cls.__dict__:
            from pgstorm.queryset.base import QuerySetWrapper

            cls.objects = QuerySetWrapper()

        return cls


class BaseModel(metaclass=ModelMeta):
    """Base for all pgstorm models. Maps type annotations to Field descriptors via ModelMeta metaclass. cls.fields is a dict of field_name -> Field."""

    objects: ClassVar[QuerySet[Self]]
    fields: ClassVar[dict[str, Field]]

    def __init__(self, **kwargs: Any) -> None:
        """Accept keyword args for Model.objects.create(**kwargs) and manual instantiation."""
        from pgstorm.queryset.parser import _iter_model_columns

        model = type(self)
        valid_names = {attr for attr, _ in _iter_model_columns(model)}
        for name, value in kwargs.items():
            if name not in valid_names:
                raise TypeError(
                    f"{model.__name__}() got an unexpected keyword argument {name!r}"
                )
            setattr(self, name, value)

    @overload
    def create(self: Self, *, schema: str | None = None) -> Self: ...
    @overload
    def create(self: Self, *, schema: str | None = None) -> Awaitable[Self]: ...
    def create(self: Self, *, schema: str | None = None) -> Self | Awaitable[Self]:
        """
        Insert this instance. With sync engine returns Self; with async returns Awaitable[Self] — use await.
        If primary key is None it is omitted. Uses RETURNING * and updates the instance with returned values.
        """
        from pgstorm.engine.context import engine as engine_context_var
        from pgstorm.queryset.parser import (
            _instance_to_row_data,
            _iter_model_columns,
            compile_insert,
            _apply_row_to_instance,
        )
        from pgstorm.columns.base import _model_primary_key_field

        model = type(self)
        eng = engine_context_var.get()
        if eng is None:
            raise RuntimeError(
                "No engine set. Call create_engine() or engine.set(engine) before using create()."
            )

        row_data = _instance_to_row_data(self, model, include_pk=True)
        pk_attr = _model_primary_key_field(model)
        all_cols = dict(_iter_model_columns(model))
        db_pk = next(
            (col.name or an for an, col in all_cols.items() if an == pk_attr),
            pk_attr,
        )
        if row_data.get(db_pk) is None:
            row_data = {k: v for k, v in row_data.items() if k != db_pk}
        if not row_data:
            raise ValueError("No columns to insert")
        compiled = compile_insert(
            model,
            [row_data],
            schema=schema,
            returning=True,
            extra={"instance": self, "objs": [self]},
        )

        def then(result: list | None) -> Self:
            if result and len(result) == 1:
                _apply_row_to_instance(self, result[0], model)
            return self

        if eng.is_async:

            async def _run() -> Self:
                result = await eng.execute(compiled)
                return then(result)

            return _run()
        return then(eng.execute(compiled))

    @overload
    def update(self: Self, *, schema: str | None = None) -> Self: ...
    @overload
    def update(self: Self, *, schema: str | None = None) -> Awaitable[Self]: ...
    def update(self: Self, *, schema: str | None = None) -> Self | Awaitable[Self]:
        """
        Update this instance by primary key. With sync engine returns Self; with async returns Awaitable[Self] — use await.
        Instance must have a non-None primary key. Uses RETURNING * and updates the instance.
        """
        from pgstorm.engine.context import engine as engine_context_var
        from pgstorm.queryset.parser import (
            _instance_to_row_data,
            compile_update_one,
            _apply_row_to_instance,
        )
        from pgstorm.columns.base import _model_primary_key_field

        model = type(self)
        pk_attr = _model_primary_key_field(model)
        pk_value = getattr(self, f"_pgstorm_value_{pk_attr}", None) or getattr(
            self, pk_attr, None
        )
        if pk_value is None:
            raise ValueError(
                f"Cannot update: {pk_attr} is None. Instance must be persisted first."
            )

        eng = engine_context_var.get()
        if eng is None:
            raise RuntimeError(
                "No engine set. Call create_engine() or engine.set(engine) before using update()."
            )

        row_data = _instance_to_row_data(self, model, include_pk=True)
        compiled = compile_update_one(
            model,
            row_data,
            pk_value,
            schema=schema,
            returning=True,
            extra={"instance": self},
        )

        def then(result: list | None) -> Self:
            if result and len(result) == 1:
                _apply_row_to_instance(self, result[0], model)
            return self

        if eng.is_async:

            async def _run() -> Self:
                result = await eng.execute(compiled)
                return then(result)

            return _run()
        return then(eng.execute(compiled))

    @overload
    def refresh_from_db(self: Self, *, schema: str | None = None) -> Self: ...
    @overload
    def refresh_from_db(
        self: Self, *, schema: str | None = None
    ) -> Awaitable[Self]: ...
    def refresh_from_db(
        self: Self, *, schema: str | None = None
    ) -> Self | Awaitable[Self]:
        """
        Reload this instance from the database. With sync engine returns Self; with async returns Awaitable[Self] — use await.
        Instance must have a non-None primary key. Raises RuntimeError if the record no longer exists.
        """
        from pgstorm import operator as op
        from pgstorm.engine.context import engine as engine_context_var
        from pgstorm.functions.expression import Expression
        from pgstorm.queryset.parser import _apply_row_to_instance, compile_queryset
        from pgstorm.queryset.base import QuerySet
        from pgstorm.columns.base import _model_primary_key_field

        model = type(self)
        pk_attr = _model_primary_key_field(model)
        pk_value = getattr(self, f"_pgstorm_value_{pk_attr}", None) or getattr(
            self, pk_attr, None
        )
        if pk_value is None:
            raise ValueError(
                f"Cannot refresh: {pk_attr} is None. Instance must be persisted first."
            )

        eng = engine_context_var.get()
        if eng is None:
            raise RuntimeError(
                "No engine set. Call create_engine() or engine.set(engine) before using refresh_from_db()."
            )

        pk_col = getattr(model, pk_attr)
        if hasattr(pk_col, "__get__"):
            pk_col = pk_col.__get__(None, model)
        qs = QuerySet(model)
        qs._schema = schema
        qs._filters = [Expression(pk_col, op.EQ, pk_value)]
        qs._limit = 1
        compiled = compile_queryset(qs)

        def then(rows: list | None) -> Self:
            if not rows:
                raise RuntimeError(
                    f"Record with {pk_attr}={pk_value} no longer exists."
                )
            _apply_row_to_instance(self, rows[0], model)
            return self

        if eng.is_async:

            async def _run() -> Self:
                rows = await eng.execute(compiled)
                return then(rows)

            return _run()
        return then(eng.execute(compiled))

    @overload
    def delete(self: Self, *, schema: str | None = None) -> None: ...
    @overload
    def delete(self: Self, *, schema: str | None = None) -> Awaitable[None]: ...
    def delete(self: Self, *, schema: str | None = None) -> None | Awaitable[None]:
        """
        Delete this instance by primary key. With sync engine returns None; with async returns Awaitable[None] — use await.
        Instance must have a non-None primary key.
        """
        from pgstorm.engine.context import engine as engine_context_var
        from pgstorm.queryset.parser import compile_delete_by_pk
        from pgstorm.columns.base import _model_primary_key_field

        model = type(self)
        pk_attr = _model_primary_key_field(model)
        pk_value = getattr(self, f"_pgstorm_value_{pk_attr}", None) or getattr(
            self, pk_attr, None
        )
        if pk_value is None:
            raise ValueError(
                f"Cannot delete: {pk_attr} is None. Instance must be persisted first."
            )

        eng = engine_context_var.get()
        if eng is None:
            raise RuntimeError(
                "No engine set. Call create_engine() or engine.set(engine) before using delete()."
            )

        compiled = compile_delete_by_pk(model, pk_value, schema=schema)
        if eng.is_async:

            async def _run() -> None:
                await eng.execute(compiled)

            return _run()
        eng.execute(compiled)
        return None

    @overload
    def __get__(self, obj: None, objtype: type | None = None) -> type[Self]: ...
    @overload
    def __get__(self, obj: object, objtype: type | None = None) -> Self: ...
    def __get__(
        self, obj: object | None, objtype: type | None = None
    ) -> type[Self] | Self:
        if obj is None:
            return self  # type: ignore[return-value]
        return obj  # type: ignore[return-value]
