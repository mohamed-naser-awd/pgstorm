"""PostgreSQL date/time types: date, time, timetz, timestamp, timestamptz, interval."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Optional

from pgstorm.columns.base import Column, ColumnDescriptor


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


# --- Date ---
class DateColumn(_ComparableLookupsMixin, Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="DATE", python_type=date, **kwargs)


class DateDescriptor(ColumnDescriptor):
    column_class = DateColumn

    def _make_column(self) -> Column:
        return DateColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- Time (without time zone) ---
class TimeColumn(_ComparableLookupsMixin, Column):
    def __init__(
        self,
        name: str = "",
        precision: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"TIME({precision})" if precision is not None else "TIME"
        super().__init__(name=name, pg_type=pg_type, python_type=time, **kwargs)
        self.precision = precision


class TimeDescriptor(ColumnDescriptor):
    column_class = TimeColumn

    def __init__(self, precision: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._precision = precision

    def _make_column(self) -> Column:
        return TimeColumn(
            precision=self._precision,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- Time with time zone (timetz) ---
class TimeTZColumn(_ComparableLookupsMixin, Column):
    def __init__(
        self,
        name: str = "",
        precision: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"TIME({precision}) WITH TIME ZONE" if precision is not None else "TIME WITH TIME ZONE"
        super().__init__(name=name, pg_type=pg_type, python_type=time, **kwargs)
        self.precision = precision


class TimeTZDescriptor(ColumnDescriptor):
    column_class = TimeTZColumn

    def __init__(self, precision: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._precision = precision

    def _make_column(self) -> Column:
        return TimeTZColumn(
            precision=self._precision,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- Timestamp (without time zone) ---
class TimestampColumn(_ComparableLookupsMixin, Column):
    def __init__(
        self,
        name: str = "",
        precision: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"TIMESTAMP({precision})" if precision is not None else "TIMESTAMP"
        super().__init__(name=name, pg_type=pg_type, python_type=datetime, **kwargs)
        self.precision = precision


class TimestampDescriptor(ColumnDescriptor):
    column_class = TimestampColumn

    def __init__(self, precision: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._precision = precision

    def _make_column(self) -> Column:
        return TimestampColumn(
            precision=self._precision,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- Timestamp with time zone (timestamptz) ---
class TimestampTZColumn(_ComparableLookupsMixin, Column):
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
        super().__init__(name=name, pg_type=pg_type, python_type=datetime, **kwargs)
        self.precision = precision


class TimestampTZDescriptor(ColumnDescriptor):
    column_class = TimestampTZColumn

    def __init__(self, precision: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._precision = precision

    def _make_column(self) -> Column:
        return TimestampTZColumn(
            precision=self._precision,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- Interval ---
class IntervalColumn(_ComparableLookupsMixin, Column):
    def __init__(
        self,
        name: str = "",
        fields: Optional[str] = None,
        precision: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = _interval_pg_type(fields=fields, precision=precision)
        super().__init__(name=name, pg_type=pg_type, python_type=timedelta, **kwargs)
        self.fields = fields
        self.precision = precision


class IntervalDescriptor(ColumnDescriptor):
    column_class = IntervalColumn

    def __init__(
        self,
        fields: Optional[str] = None,
        precision: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._fields = fields
        self._precision = precision

    def _make_column(self) -> Column:
        return IntervalColumn(
            fields=self._fields,
            precision=self._precision,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )
