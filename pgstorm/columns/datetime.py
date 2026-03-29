"""PostgreSQL date/time types: date, time, timetz, timestamp, timestamptz, interval."""
from __future__ import annotations

import datetime as _dt
from typing import Any, Optional

from pgstorm.columns.base import ScalarField


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


def _interval_pg_type(
    fields: Optional[str] = None,
    precision: Optional[int] = None,
) -> str:
    parts = ["INTERVAL"]
    if fields:
        parts[0] = f"INTERVAL {fields}"
    if precision is not None:
        parts.append(f"({precision})")
    return " ".join(parts) if len(parts) > 1 else parts[0]


class Date(_ComparableLookupsMixin, ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="DATE", python_type=_dt.date, **kwargs)


class Time(_ComparableLookupsMixin, ScalarField):
    def __init__(
        self,
        name: str = "",
        precision: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"TIME({precision})" if precision is not None else "TIME"
        super().__init__(name=name, pg_type=pg_type, python_type=_dt.time, **kwargs)
        self.precision = precision


class TimeTZ(_ComparableLookupsMixin, ScalarField):
    def __init__(
        self,
        name: str = "",
        precision: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"TIME({precision}) WITH TIME ZONE" if precision is not None else "TIME WITH TIME ZONE"
        super().__init__(name=name, pg_type=pg_type, python_type=_dt.time, **kwargs)
        self.precision = precision


class Timestamp(_ComparableLookupsMixin, ScalarField):
    def __init__(
        self,
        name: str = "",
        precision: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"TIMESTAMP({precision})" if precision is not None else "TIMESTAMP"
        super().__init__(name=name, pg_type=pg_type, python_type=_dt.datetime, **kwargs)
        self.precision = precision


class TimestampTZ(_ComparableLookupsMixin, ScalarField):
    def __init__(
        self,
        name: str = "",
        precision: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = (
            f"TIMESTAMP({precision}) WITH TIME ZONE"
            if precision is not None
            else "TIMESTAMP WITH TIME ZONE"
        )
        super().__init__(name=name, pg_type=pg_type, python_type=_dt.datetime, **kwargs)
        self.precision = precision


class Interval(_ComparableLookupsMixin, ScalarField):
    def __init__(
        self,
        name: str = "",
        fields: Optional[str] = None,
        precision: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = _interval_pg_type(fields=fields, precision=precision)
        super().__init__(name=name, pg_type=pg_type, python_type=_dt.timedelta, **kwargs)
        self.fields = fields
        self.precision = precision


DateColumn = DateDescriptor = Date
TimeColumn = TimeDescriptor = Time
TimeTZColumn = TimeTZDescriptor = TimeTZ
TimestampColumn = TimestampDescriptor = Timestamp
TimestampTZColumn = TimestampTZDescriptor = TimestampTZ
IntervalColumn = IntervalDescriptor = Interval
