"""PostgreSQL full-text search types: tsvector, tsquery."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import Column, ColumnDescriptor


class TsVectorColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="TSVECTOR", python_type=str, **kwargs)


class TsVectorDescriptor(ColumnDescriptor):
    column_class = TsVectorColumn

    def _make_column(self) -> Column:
        return TsVectorColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class TsQueryColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="TSQUERY", python_type=str, **kwargs)


class TsQueryDescriptor(ColumnDescriptor):
    column_class = TsQueryColumn

    def _make_column(self) -> Column:
        return TsQueryColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )
