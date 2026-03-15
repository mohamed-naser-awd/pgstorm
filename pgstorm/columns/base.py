"""
Base Column and Field for pgstorm.
Each type has a Column (holds DDL/type info) and a Field subclass (descriptor for model attributes).
Field.generate_descriptor(annotation) turns an annotation into a descriptor instance.
"""
from __future__ import annotations

import copy
from typing import Annotated as TypingAnnotated, Any, Callable, Generic, Optional, overload, Type, TypeVar, TypeVarTuple, get_origin, get_args

T = TypeVar("T")
V = TypeVar("V")  # Value type (e.g. str, int) when accessed on an instance
C = TypeVar("C", bound="Column")  # Column type when accessed on the class
M = TypeVar("M")  # Target model type for RelationField (e.g. User)
Meta = TypeVarTuple("Meta")  # Optional metadata: ON_DELETE_*, FK_FIELD(...), etc.


class FKFieldRef:
    """
    Sentinel for Annotated metadata: FK references a specific field on the target model.
    Created via types.FK_FIELD("field_name").
    """

    __slots__ = ("field_name",)

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name

    def __repr__(self) -> str:
        return f"FK_FIELD({self.field_name!r})"


class FKColumnRef:
    """
    Sentinel for Annotated metadata: the actual DB column name for a ForeignKey/OneToOne.
    Created via types.FK_COLUMN("column_name").
    When not specified, defaults to {attr_name}_id (e.g. user -> user_id).
    """

    __slots__ = ("column_name",)

    def __init__(self, column_name: str) -> None:
        self.column_name = column_name

    def __repr__(self) -> str:
        return f"FK_COLUMN({self.column_name!r})"


class ReverseNameRef:
    """
    Sentinel for Annotated metadata: name of the reverse relation on the target model.
    Created via types.ReverseName("attr_name").
    E.g. ForeignKey[User, ReverseName("user_profile")] adds user.user_profile -> UserProfile.
    When not specified, defaults to the source model's table name.
    """

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"ReverseName({self.name!r})"


class _PrimaryKeyFieldRef:
    """
    Sentinel for scalar field metadata: marks the field as primary key.
    Use: types.Integer[types.IS_PRIMARY_KEY_FIELD]
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "IS_PRIMARY_KEY_FIELD"


IS_PRIMARY_KEY_FIELD = _PrimaryKeyFieldRef()


class Self:
    """
    Sentinel for self-referential relations.
    Use: reply_to: types.ForeignKey[types.Self] or types.OneToOne[types.Self]
    """

    __slots__ = ()


class ReverseRelationDescriptor:
    """
    Descriptor added to the target model for reverse relations.
    When reverse_name is set on a ForeignKey/OneToOne, this is installed on the target
    so that user.user_profile returns the related UserProfile (or None).
    """

    __slots__ = ("_source_model", "_fk_attr", "_fk_field", "_name")

    def __init__(
        self,
        source_model: Type[Any],
        fk_attr: str,
        fk_field: str,
        name: str,
    ) -> None:
        self._source_model = source_model
        self._fk_attr = fk_attr
        self._fk_field = fk_field
        self._name = name

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Any:
        if obj is None:
            return self
        cached = getattr(obj, f"_pgstorm_value_{self._name}", None)
        if cached is not None and not _is_unset(cached):
            return cached
        match_value = getattr(obj, self._fk_field, None)
        if match_value is None:
            return None
        from pgstorm.engine.context import engine as engine_context_var

        eng = engine_context_var.get()
        if eng is None:
            return None
        fk_descriptor = getattr(self._source_model, self._fk_attr)
        if hasattr(fk_descriptor, "__get__"):
            col_ref = fk_descriptor.__get__(None, self._source_model)
        else:
            col_ref = fk_descriptor
        target_col = getattr(self._source_model, self._fk_field)
        if hasattr(target_col, "__get__"):
            target_ref = target_col.__get__(None, self._source_model)
        else:
            target_ref = target_col
        from pgstorm.functions.expression import Expression
        from pgstorm import operator as op

        qs = self._source_model.objects.filter(
            Expression(col_ref, op.EQ, match_value)
        ).limit(1)
        compiled = qs.compiled()
        rows = eng.execute(compiled)
        instances = qs._rows_to_instances(rows)
        result = instances[0] if instances else None
        if result is not None:
            setattr(obj, f"_pgstorm_value_{self._name}", result)
        return result

    def __set__(self, obj: Any, value: Any) -> None:
        setattr(obj, f"_pgstorm_value_{self._name}", value)


def _is_unset(val: Any) -> bool:
    """Sentinel for 'not yet loaded' to distinguish from None."""
    return getattr(val, "_pgstorm_unset", False)


class Column:
    """Base class for a column definition. Holds PostgreSQL type and constraints."""

    __slots__ = (
        "name",
        "pg_type",
        "python_type",
        "default",
        "nullable",
        "primary_key",
        "unique",
        "index",
        "kwargs",
    )

    # Registry of custom lookups: name -> (column_self, rhs) -> Expression.
    # Subclasses may override to add their own; use register_lookup() to add.
    _lookups: dict[str, Callable[..., Any]] = {
        "in_": lambda col, rhs: col._expr("IN", rhs),
    }
    # Merged lookups from MRO, built at class init / registration (avoid per-request work).
    _merged_lookups: dict[str, Callable[..., Any]] = {}

    def __init__(
        self,
        name: str = "",
        pg_type: str = "",
        python_type: Type[Any] = object,
        *,
        default: Any = None,
        nullable: bool = True,
        primary_key: bool = False,
        unique: bool = False,
        index: bool = False,
        **kwargs: Any,
    ) -> None:
        self.name = name
        self.pg_type = pg_type
        self.python_type = python_type
        self.default = default
        self.nullable = nullable
        self.primary_key = primary_key
        self.unique = unique
        self.index = index
        self.kwargs = kwargs

    def with_name(self, name: str) -> "Column":
        """Return a copy of this column with the given name (used when binding to model)."""
        c = copy.copy(self)
        c.name = name
        return c

    def ddl_type(self) -> str:
        """Return the PostgreSQL type string for DDL/migrations (e.g. 'INTEGER', 'VARCHAR(255)')."""
        return self.pg_type

    def _expr(self, operator: str, rhs: Any) -> Any:
        """Build an Expression for this column with the given operator and right-hand side."""
        from pgstorm.functions.expression import Expression
        return Expression(self, operator, rhs)

    def __eq__(self, rhs: Any) -> Any:
        return self._expr("=", rhs)

    def __ne__(self, rhs: Any) -> Any:
        return self._expr("!=", rhs)

    def __lt__(self, rhs: Any) -> Any:
        return self._expr("<", rhs)

    def __le__(self, rhs: Any) -> Any:
        return self._expr("<=", rhs)

    def __gt__(self, rhs: Any) -> Any:
        return self._expr(">", rhs)

    def __ge__(self, rhs: Any) -> Any:
        return self._expr(">=", rhs)

    @staticmethod
    def _merge_lookups_from_mro(cls: Type[Column]) -> dict[str, Callable[..., Any]]:
        """Merge lookups from the class MRO (subclass lookups override base). Computed at class init / registration."""
        lookups: dict[str, Callable[..., Any]] = {}
        for c in reversed(cls.__mro__):
            lookups.update(getattr(c, "_lookups", {}))
        return lookups

    @classmethod
    def _build_merged_lookups(cls: Type[Column]) -> None:
        """Set _merged_lookups on this class and all subclasses (after MRO or _lookups change)."""
        cls._merged_lookups = cls._merge_lookups_from_mro(cls)
        for sub in cls.__subclasses__():
            sub._build_merged_lookups()

    def __init_subclass__(cls: Type[Column], **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if issubclass(cls, Column):
            cls._build_merged_lookups()

    @classmethod
    def register_lookup(cls, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Register a custom lookup for this column (and subclasses that don't override _lookups).
        Usage::
            @Column.register_lookup("contains")
            def _lookup_contains(column: Column, rhs: Any):
                return column._expr("LIKE", f"%{rhs}%")
        When a subclass first registers a lookup, it gets a copy of the parent's lookups.
        """

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            base = cls.__bases__[0] if cls.__bases__ else None
            base_lookups = getattr(base, "_lookups", {}) if base else {}
            current = getattr(cls, "_lookups", None)
            if current is base_lookups:
                cls._lookups = dict(base_lookups)
            elif current is None:
                cls._lookups = {}
            cls._lookups[name] = fn
            cls._build_merged_lookups()
            return fn

        return decorator

    @staticmethod
    def _lookup_in(column: "Column", rhs: Any) -> Any:
        """IN lookup: column.in_(iterable) or column.in_(Subquery(...))."""
        from pgstorm import operator as op
        return column._expr(op.IN, rhs)

    def __getattr__(self, name: str) -> Any:
        """Resolve custom lookups so that column.my_lookup(value) returns an Expression."""
        cls = type(self)
        lookups = getattr(cls, "_merged_lookups", None)
        if lookups is None:
            cls._merged_lookups = cls._merge_lookups_from_mro(cls)
            lookups = cls._merged_lookups
        if name in lookups:
            fn = lookups[name]

            def lookup_fn(rhs: Any) -> Any:
                return fn(self, rhs)

            return lookup_fn
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}"
        )


def _model_table_name(model: type[Any]) -> str:
    """Resolve table name for a model: __table__/__tablename__ or lowercased class name."""
    explicit = getattr(model, "__tablename__", None) or getattr(model, "__table__", None)
    if isinstance(explicit, str) and explicit:
        return explicit
    return model.__name__.lower()


def _model_primary_key_field(model: type[Any]) -> str:
    """Return the primary key field name for a model, or 'id' if none found."""
    for attr_name, attr_value in vars(model).items():
        if attr_name.startswith("_"):
            continue
        if isinstance(attr_value, Field) and getattr(attr_value, "_primary_key", False):
            return attr_name
    return "id"


ScalarMeta = TypeVarTuple("ScalarMeta")  # Optional: IS_PRIMARY_KEY_FIELD for scalar types


class Field(Generic[V, C, *ScalarMeta]):
    """
    Base descriptor for model attributes. All type classes (Integer, String, etc.) inherit from Field.
    - V: value type when accessed on an instance (e.g. str, int).
    - C: column type when accessed on the class (e.g. TextColumn, IntegerColumn).
    - get_pg_type(): returns the PostgreSQL type string for migrations/DDL.
    - get_column(): returns the actual Column instance for this attribute.
    """

    column_class: Type[Column] = Column

    def __init__(
        self,
        *,
        default: Any = None,
        nullable: bool = True,
        primary_key: bool = False,
        unique: bool = False,
        index: bool = False,
        **kwargs: Any,
    ) -> None:
        self._default = default
        self._nullable = nullable
        self._primary_key = primary_key
        self._unique = unique
        self._index = index
        self._kwargs = kwargs
        self._column: Optional[Column] = None
        self._name: Optional[str] = None

    @classmethod
    def generate_descriptor(cls, field_annotation: Any) -> Optional[Field]:
        """
        Build a descriptor instance from a field annotation.
        - ForeignKey[Model], ForeignKey[Model, ON_DELETE_CASCADE, FK_FIELD("x")], etc.
        - OneToOne[Model], ManyToMany[Model] with optional metadata in the same way.
        - Subclass of Field -> return instance of that type.
        - Field instance (e.g. Varchar(20), TimestampTZ(default=Now())) -> return as-is.
        Returns None if the annotation is not a pgstorm field type.
        """
        if isinstance(field_annotation, Field):
            return field_annotation
        origin = get_origin(field_annotation)
        # Union / X | None: use inner type with nullable=True
        if origin is not None:
            try:
                from types import UnionType
                is_union = origin is UnionType
            except ImportError:
                is_union = False
            if is_union or (hasattr(origin, "__origin__") and "Union" in str(origin)):
                args = get_args(field_annotation)
                non_none = [a for a in args if a is not type(None)]
                if len(non_none) == 1:
                    inner = cls.generate_descriptor(non_none[0])
                    if inner is not None and hasattr(inner, "_nullable"):
                        inner._nullable = True
                    return inner
        if origin is not None:
            from typing import Union
            if origin is Union:
                args = get_args(field_annotation)
                non_none = [a for a in args if a is not type(None)]
                if len(non_none) == 1:
                    inner = cls.generate_descriptor(non_none[0])
                    if inner is not None and hasattr(inner, "_nullable"):
                        inner._nullable = True
                    return inner
        if origin is TypingAnnotated:
            args = get_args(field_annotation)
            if not args:
                return None
            inner_type = args[0]
            # Check metadata for relation types: Annotated[User, ForeignKey[User, ...]]
            # Type checkers use the first arg (User) as the attribute type for profile.user
            relation_origins = (ForeignKey, OneToOne, ManyToMany)
            for meta in args[1:]:
                meta_origin = get_origin(meta)
                if meta_origin in relation_origins:
                    meta_args = get_args(meta)
                    if meta_args and isinstance(meta_args[0], type):
                        target_model = meta_args[0]
                        metadata = tuple(meta_args[1:]) if len(meta_args) > 1 else ()
                        if meta_origin is ForeignKey:
                            return ForeignKey(target_model=target_model, metadata=metadata)
                        if meta_origin is OneToOne:
                            return OneToOne(target_model=target_model, metadata=metadata)
                        if meta_origin is ManyToMany:
                            return ManyToMany(target_model=target_model, metadata=metadata)
            return cls.generate_descriptor(inner_type)
        # ForeignKey[Model], ForeignKey[Model, meta, ...], OneToOne[...], ManyToMany[...]
        relation_origins = (ForeignKey, OneToOne, ManyToMany)
        if origin is not None and origin in relation_origins:
            args = get_args(field_annotation)
            if args and isinstance(args[0], type):
                target_model = args[0]
                metadata = tuple(args[1:]) if len(args) > 1 else ()
                if origin is ForeignKey:
                    return ForeignKey(target_model=target_model, metadata=metadata)
                if origin is OneToOne:
                    return OneToOne(target_model=target_model, metadata=metadata)
                if origin is ManyToMany:
                    return ManyToMany(target_model=target_model, metadata=metadata)
        # Scalar types with metadata: Integer[IS_PRIMARY_KEY_FIELD], etc.
        if origin is not None and isinstance(origin, type) and issubclass(origin, Field):
            args = get_args(field_annotation)
            primary_key = any(arg is IS_PRIMARY_KEY_FIELD for arg in (args or ()))
            return origin(primary_key=primary_key) if primary_key else origin()
        if isinstance(field_annotation, type) and issubclass(field_annotation, Field):
            return field_annotation()
        return None

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name
        self._column = self._make_column().with_name(name)

    def _make_column(self) -> Column:
        """Build the Column instance. Override in subclasses to set pg_type and python_type."""
        return self.column_class(
            pg_type="",
            python_type=object,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )

    def get_pg_type(self) -> str:
        """Return the PostgreSQL data type string for migrations/DDL."""
        if self._column is None:
            col = self._make_column()
            return col.ddl_type()
        return self._column.ddl_type()

    def get_column(self) -> Optional[Column]:
        """Return the actual Column instance (after descriptor is bound to a class)."""
        return self._column

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None) -> C: ...
    @overload
    def __get__(self, obj: Any, objtype: Optional[type] = None) -> V: ...
    def __get__(self, obj: Any, objtype: Optional[type] = None) -> V | C:
        if obj is None:
            from pgstorm.functions.expression import BoundColumnRef
            column = self._column if self._column is not None else self._make_column()
            attr_name = self._name
            if attr_name is None and objtype is not None:
                for name, value in vars(objtype).items():
                    if value is self:
                        attr_name = name
                        break
            return self._bound_column_ref(objtype, attr_name or "", column)  # type: ignore[return-value]
        return getattr(obj, f"_pgstorm_value_{self._name}", self._default)  # type: ignore[return-value]

    def _bound_column_ref(self, objtype: type[Any], attr_name: str, column: Column) -> Any:
        """Build the BoundColumnRef for class-level access. Override in RelationField to pass target_model."""
        from pgstorm.functions.expression import BoundColumnRef
        return BoundColumnRef(objtype, attr_name, column)

    def __set__(self, obj: Any, value: Any) -> None:
        setattr(obj, f"_pgstorm_value_{self._name}", value)

    def __delete__(self, obj: Any) -> None:
        if hasattr(obj, f"_pgstorm_value_{self._name}"):
            delattr(obj, f"_pgstorm_value_{self._name}")


class RelationField(Field[Any, Type[M]], Generic[M]):
    """
    Base for ForeignKey and OneToOne. When accessed on the class (e.g. UserProfile.user),
    returns Type[M] so that .email etc. are typed as the target model's Column descriptors.
    """

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None) -> Type[M]: ...
    @overload
    def __get__(self, obj: Any, objtype: Optional[type] = None) -> M: ...
    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Type[M] | M:
        return super().__get__(obj, objtype)

    # Known on_delete metadata values (str)
    _ON_DELETE_VALUES = frozenset({"RESTRICT", "CASCADE", "SET NULL", "NO ACTION"})

    def __init__(
        self,
        *,
        target_model: Type[Any],
        metadata: tuple = (),
        fk_field: Optional[str] = None,
        fk_column: Optional[str] = None,
        on_delete: Optional[str] = None,
        reverse_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._target_model = target_model
        self._metadata: tuple = metadata
        self._fk_field: Optional[str] = fk_field
        self._fk_column: Optional[str] = fk_column
        self._on_delete: Optional[str] = on_delete
        self._reverse_name: Optional[str] = reverse_name

    @classmethod
    def _parse_metadata(
        cls, metadata: tuple
    ) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Extract fk_field, fk_column, on_delete, and reverse_name from metadata."""
        fk_field: Optional[str] = None
        fk_column: Optional[str] = None
        on_delete: Optional[str] = None
        reverse_name: Optional[str] = None
        for item in metadata:
            if isinstance(item, FKFieldRef):
                fk_field = item.field_name
            elif isinstance(item, FKColumnRef):
                fk_column = item.column_name
            elif isinstance(item, str) and item in cls._ON_DELETE_VALUES:
                on_delete = item
            elif isinstance(item, ReverseNameRef):
                reverse_name = item.name
        return fk_field, fk_column, on_delete, reverse_name

    def _apply_metadata(self) -> None:
        """Parse _metadata and set _fk_field, _fk_column, _on_delete, and _reverse_name."""
        if not self._metadata:
            return
        fk_field, fk_column, on_delete, reverse_name = self._parse_metadata(self._metadata)
        if fk_field is not None:
            self._fk_field = fk_field
        if fk_column is not None:
            self._fk_column = fk_column
        if on_delete is not None:
            self._on_delete = on_delete
        if reverse_name is not None:
            self._reverse_name = reverse_name

    def _make_column(self) -> Column:
        self._apply_metadata()
        fk_field = self._fk_field or _model_primary_key_field(self._target_model)
        # Resolve pg_type from target model's referenced field
        pg_type = "BIGINT"
        python_type: Type[Any] = int
        if fk_field:
            try:
                from pgstorm.models import BaseModel

                if isinstance(self._target_model, type) and issubclass(self._target_model, BaseModel):
                    target_descriptor = getattr(self._target_model, fk_field, None)
                    if target_descriptor is not None and isinstance(target_descriptor, Field):
                        col = target_descriptor.get_column() or target_descriptor._make_column()
                        pg_type = col.ddl_type()
                        python_type = col.python_type
            except (ImportError, TypeError):
                pass
        return self.column_class(
            pg_type=pg_type,
            python_type=python_type,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )

    def _bound_column_ref(self, objtype: type[Any], attr_name: str, column: Column) -> Any:
        """Return a BoundColumnRef that knows the related model so .attr (e.g. .email) resolves on target."""
        from pgstorm.functions.expression import BoundColumnRef
        return BoundColumnRef(
            objtype,
            attr_name,
            column,
            target_model=self._target_model,
            relation_attr=attr_name,
        )

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name
        if self._target_model is Self:
            self._target_model = owner
        self._apply_metadata()
        # Use {attr}_id as DB column by default (e.g. user -> user_id), or FK_COLUMN override
        db_column = self._fk_column if self._fk_column is not None else f"{name}_id"
        self._column = self._make_column().with_name(db_column)
        self._register_reverse_descriptor(owner, name)

    def _register_reverse_descriptor(self, owner: type, fk_attr_name: str) -> None:
        """Register a reverse relation descriptor on the target model."""
        reverse_name = self._reverse_name or _model_table_name(owner)
        if reverse_name in vars(self._target_model):
            return
        fk_field = self._fk_field or _model_primary_key_field(self._target_model)
        desc = _ReverseRelationDescriptor(
            source_model=owner,
            fk_attr_name=fk_attr_name,
            fk_field=fk_field,
        )
        desc.__set_name__(self._target_model, reverse_name)
        setattr(self._target_model, reverse_name, desc)


class _ReverseRelationDescriptor:
    """
    Descriptor for the reverse side of a ForeignKey/OneToOne.
    E.g. UserProfile.user -> User with ReverseName("user_profile") adds User.user_profile -> UserProfile.
    """

    __slots__ = ("_source_model", "_fk_attr_name", "_fk_field", "_name")

    def __init__(
        self,
        *,
        source_model: type[Any],
        fk_attr_name: str,
        fk_field: str = "id",
    ) -> None:
        self._source_model = source_model
        self._fk_attr_name = fk_attr_name
        self._fk_field = fk_field
        self._name: Optional[str] = None

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Any:
        if obj is None:
            return self
        cache_attr = f"_pgstorm_value_{self._name}"
        if hasattr(obj, cache_attr):
            return getattr(obj, cache_attr)
        match_value = getattr(obj, self._fk_field, None)
        if match_value is None:
            return None
        from pgstorm.engine.context import engine as engine_context_var

        eng = engine_context_var.get()
        if eng is None:
            return None
        fk_descriptor = getattr(self._source_model, self._fk_attr_name)
        bound = fk_descriptor.__get__(None, self._source_model)
        from pgstorm.functions.expression import Expression
        from pgstorm import operator as op

        qs = self._source_model.objects.filter(
            Expression(bound, op.EQ, match_value)
        ).limit(1)
        compiled = qs.compiled()
        rows = eng.execute(compiled) if not eng.is_async else None
        if eng.is_async:
            return None  # Lazy load not supported for async yet
        instances = qs._rows_to_instances(rows or [])
        result = instances[0] if instances else None
        if result is not None:
            setattr(obj, cache_attr, result)
        return result

    def __set__(self, obj: Any, value: Any) -> None:
        setattr(obj, f"_pgstorm_value_{self._name}", value)


class ForeignKey(RelationField[M], Generic[M, *Meta]):
    """Many-to-one relation. Use: user: types.ForeignKey[User] or types.ForeignKey[User, types.ON_DELETE_CASCADE, types.FK_FIELD("email")]."""

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None) -> Type[M]: ...
    @overload
    def __get__(self, obj: Any, objtype: Optional[type] = None) -> M: ...
    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Type[M] | M:
        return super().__get__(obj, objtype)


class OneToOne(RelationField[M], Generic[M, *Meta]):
    """One-to-one relation. Same as FK but unique. Use: profile: types.OneToOne[UserProfile] or with metadata in brackets."""

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None) -> Type[M]: ...
    @overload
    def __get__(self, obj: Any, objtype: Optional[type] = None) -> M: ...
    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Type[M] | M:
        return super().__get__(obj, objtype)

    def __init__(self, *, target_model: Type[Any], metadata: tuple = (), **kwargs: Any) -> None:
        super().__init__(target_model=target_model, metadata=metadata, unique=True, **kwargs)


class _ManyToManyProxy:
    """Proxy so that Model.tags.column_name returns BoundColumnRef for the target model's column (for typing + filters)."""

    __slots__ = ("owner_model", "attr_name", "target_model")

    def __init__(self, owner_model: type[Any], attr_name: str, target_model: Type[Any]) -> None:
        self.owner_model = owner_model
        self.attr_name = attr_name
        self.target_model = target_model

    def __getattr__(self, name: str) -> Any:
        from pgstorm.functions.expression import BoundColumnRef
        attr = self.target_model.__dict__.get(name)
        if isinstance(attr, Field):
            col = attr.get_column() or attr._make_column()
            return BoundColumnRef(
                self.owner_model,
                self.attr_name,
                col,
                target_model=self.target_model,
                relation_attr=name,
            )
        return getattr(self.target_model, name)


class ManyToMany(Field[Any, Type[M]], Generic[M, *Meta]):
    """
    Many-to-many relation. No column on this model; relationship is via a through table.
    Use: tags: types.ManyToMany[Tag] or types.ManyToMany[Tag, ...metadata]. Class access returns Type[M].
    """

    _target_model: Type[Any]
    _metadata: tuple
    _name: Optional[str]

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None) -> Type[M]: ...
    @overload
    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Any: ...
    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Any:
        if obj is not None:
            return getattr(obj, f"_pgstorm_value_{self._name}", None)
        return _ManyToManyProxy(objtype or object, self._name or "", self._target_model)

    def __init__(self, *, target_model: Type[Any], metadata: tuple = (), **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._target_model = target_model
        self._metadata = metadata
        self._name = None

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name
        # No column for many-to-many

    def get_column(self) -> Optional[Column]:
        return None

    def get_pg_type(self) -> str:
        return ""


# Backward compatibility: ColumnDescriptor is Field.
ColumnDescriptor = Field
