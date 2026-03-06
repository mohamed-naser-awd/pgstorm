"""PostgreSQL boolean type."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import Column, ColumnDescriptor


class BooleanColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="BOOLEAN", python_type=bool, **kwargs)

    def _expr(self, operator: str, rhs: Any) -> Any:
        from pgstorm.functions.expression import Expression

        return Expression(self, operator, rhs)

    def eq(self, rhs: Any) -> Any:
        from pgstorm import operator as op

        return self._expr(op.EQ, rhs)

    def ne(self, rhs: Any) -> Any:
        from pgstorm import operator as op

        return self._expr(op.NE, rhs)


class BooleanDescriptor(ColumnDescriptor):
    column_class = BooleanColumn

    def _make_column(self) -> Column:
        return BooleanColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )
