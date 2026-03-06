"""PostgreSQL binary type: bytea."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import Column, ColumnDescriptor


class ByteaColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="BYTEA", python_type=bytes, **kwargs)


class ByteaDescriptor(ColumnDescriptor):
    column_class = ByteaColumn

    def _make_column(self) -> Column:
        return ByteaColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )
