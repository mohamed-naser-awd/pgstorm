"""PostgreSQL JSON types: json, jsonb."""
from __future__ import annotations

from typing import Any, Dict, List, Union

from pgstorm.columns.base import Column, ColumnDescriptor

# Python type for JSON: dict, list, str, int, float, bool, None
JsonPythonType = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


class JsonColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="JSON", python_type=dict, **kwargs)


class JsonDescriptor(ColumnDescriptor):
    column_class = JsonColumn

    def _make_column(self) -> Column:
        return JsonColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class JsonbColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="JSONB", python_type=dict, **kwargs)


class JsonbDescriptor(ColumnDescriptor):
    column_class = JsonbColumn

    def _make_column(self) -> Column:
        return JsonbColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )
