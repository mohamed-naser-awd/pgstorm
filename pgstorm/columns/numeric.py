"""PostgreSQL numeric types: smallint, integer, bigint, serials, real, double precision, numeric."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Generic, Optional

from pgstorm.columns.base import ScalarField, ScalarMeta


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


class SmallInt(_ComparableLookupsMixin, ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="SMALLINT", python_type=int, **kwargs)


class Integer(_ComparableLookupsMixin, ScalarField, Generic[*ScalarMeta]):
    """Supports types.Integer[types.IS_PRIMARY_KEY_FIELD] for primary key fields."""

    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="INTEGER", python_type=int, **kwargs)


class BigInt(_ComparableLookupsMixin, ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="BIGINT", python_type=int, **kwargs)


class SmallSerial(_ComparableLookupsMixin, ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="SMALLSERIAL", python_type=int, **kwargs)


class Serial(_ComparableLookupsMixin, ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="SERIAL", python_type=int, **kwargs)


class BigSerial(_ComparableLookupsMixin, ScalarField, Generic[*ScalarMeta]):
    """Supports types.BigSerial[types.IS_PRIMARY_KEY_FIELD] for primary key fields."""

    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="BIGSERIAL", python_type=int, **kwargs)


class Real(_ComparableLookupsMixin, ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="REAL", python_type=float, **kwargs)


class DoublePrecision(_ComparableLookupsMixin, ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="DOUBLE PRECISION", python_type=float, **kwargs)


class Numeric(_ComparableLookupsMixin, ScalarField):
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


SmallIntColumn = SmallIntDescriptor = SmallInt
IntegerColumn = IntegerDescriptor = Integer
BigIntColumn = BigIntDescriptor = BigInt
SmallSerialColumn = SmallSerialDescriptor = SmallSerial
SerialColumn = SerialDescriptor = Serial
BigSerialColumn = BigSerialDescriptor = BigSerial
RealColumn = RealDescriptor = Real
DoublePrecisionColumn = DoublePrecisionDescriptor = DoublePrecision
NumericColumn = NumericDescriptor = Numeric
DecimalColumn = DecimalDescriptor = Numeric
