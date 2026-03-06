"""PostgreSQL monetary type: money."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import Column, ColumnDescriptor


class MoneyColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="MONEY", python_type=str, **kwargs)


class MoneyDescriptor(ColumnDescriptor):
    column_class = MoneyColumn

    def _make_column(self) -> Column:
        return MoneyColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )
