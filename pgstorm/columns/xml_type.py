"""PostgreSQL XML type."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import Column, ColumnDescriptor


class XmlColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="XML", python_type=str, **kwargs)


class XmlDescriptor(ColumnDescriptor):
    column_class = XmlColumn

    def _make_column(self) -> Column:
        return XmlColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )
