"""PostgreSQL numeric types: smallint, integer, bigint, serials, real, double precision, numeric."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Generic, Optional

from pgstorm.columns.base import Column, ColumnDescriptor, ScalarMeta


class _ComparableLookupsMixin:
    def _expr(self, operator: str, rhs: Any) -> Any:
        from pgstorm.functions.expression import Expression

        return Expression(self, operator, rhs)

    def eq(self, rhs: Any) -> Any:
        from pgstorm import operator as op

        return self._expr(op.EQ, rhs)

    def ne(self, rhs: Any) -> Any:
        from pgstorm import operator as op

        return self._expr(op.NE, rhs)

    def lt(self, rhs: Any) -> Any:
        from pgstorm import operator as op

        return self._expr(op.LT, rhs)

    def lte(self, rhs: Any) -> Any:
        from pgstorm import operator as op

        return self._expr(op.LTE, rhs)

    def gt(self, rhs: Any) -> Any:
        from pgstorm import operator as op

        return self._expr(op.GT, rhs)

    def gte(self, rhs: Any) -> Any:
        from pgstorm import operator as op

        return self._expr(op.GTE, rhs)


# --- SmallInt ---
class SmallIntColumn(_ComparableLookupsMixin, Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="SMALLINT", python_type=int, **kwargs)


class SmallIntDescriptor(ColumnDescriptor[int, SmallIntColumn]):
    column_class = SmallIntColumn

    def _make_column(self) -> Column:
        return SmallIntColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- Integer ---
class IntegerColumn(_ComparableLookupsMixin, Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="INTEGER", python_type=int, **kwargs)


class IntegerDescriptor(ColumnDescriptor[int, IntegerColumn], Generic[*ScalarMeta]):
    """Supports types.Integer[types.IS_PRIMARY_KEY_FIELD] for primary key fields."""
    column_class = IntegerColumn

    def _make_column(self) -> Column:
        return IntegerColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- BigInt ---
class BigIntColumn(_ComparableLookupsMixin, Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="BIGINT", python_type=int, **kwargs)


class BigIntDescriptor(ColumnDescriptor[int, BigIntColumn]):
    column_class = BigIntColumn

    def _make_column(self) -> Column:
        return BigIntColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- SmallSerial ---
class SmallSerialColumn(_ComparableLookupsMixin, Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="SMALLSERIAL", python_type=int, **kwargs)


class SmallSerialDescriptor(ColumnDescriptor[int, SmallSerialColumn]):
    column_class = SmallSerialColumn

    def _make_column(self) -> Column:
        return SmallSerialColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- Serial ---
class SerialColumn(_ComparableLookupsMixin, Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="SERIAL", python_type=int, **kwargs)


class SerialDescriptor(ColumnDescriptor[int, SerialColumn]):
    column_class = SerialColumn

    def _make_column(self) -> Column:
        return SerialColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- BigSerial ---
class BigSerialColumn(_ComparableLookupsMixin, Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="BIGSERIAL", python_type=int, **kwargs)


class BigSerialDescriptor(ColumnDescriptor[int, BigSerialColumn], Generic[*ScalarMeta]):
    """Supports types.BigSerial[types.IS_PRIMARY_KEY_FIELD] for primary key fields."""
    column_class = BigSerialColumn

    def _make_column(self) -> Column:
        return BigSerialColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- Real (float4) ---
class RealColumn(_ComparableLookupsMixin, Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="REAL", python_type=float, **kwargs)


class RealDescriptor(ColumnDescriptor[float, RealColumn]):
    column_class = RealColumn

    def _make_column(self) -> Column:
        return RealColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- Double Precision (float8) ---
class DoublePrecisionColumn(_ComparableLookupsMixin, Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="DOUBLE PRECISION", python_type=float, **kwargs)


class DoublePrecisionDescriptor(ColumnDescriptor[float, DoublePrecisionColumn]):
    column_class = DoublePrecisionColumn

    def _make_column(self) -> Column:
        return DoublePrecisionColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- Numeric / Decimal ---
class NumericColumn(_ComparableLookupsMixin, Column):
    def __init__(
        self,
        name: str = "",
        precision: Optional[int] = None,
        scale: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        if precision is not None and scale is not None:
            pg_type = f"NUMERIC({precision},{scale})"
        elif precision is not None:
            pg_type = f"NUMERIC({precision})"
        else:
            pg_type = "NUMERIC"
        super().__init__(name=name, pg_type=pg_type, python_type=Decimal, **kwargs)
        self.precision = precision
        self.scale = scale


class NumericDescriptor(ColumnDescriptor[Decimal, NumericColumn]):
    column_class = NumericColumn

    def __init__(
        self,
        precision: Optional[int] = None,
        scale: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._precision = precision
        self._scale = scale

    def _make_column(self) -> Column:
        return NumericColumn(
            precision=self._precision,
            scale=self._scale,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# Convenience aliases
DecimalColumn = NumericColumn
DecimalDescriptor = NumericDescriptor
