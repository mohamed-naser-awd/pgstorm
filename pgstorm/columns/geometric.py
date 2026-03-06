"""PostgreSQL geometric types: point, line, lseg, box, path, polygon, circle."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import Column, ColumnDescriptor


class PointColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="POINT", python_type=str, **kwargs)


class PointDescriptor(ColumnDescriptor):
    column_class = PointColumn

    def _make_column(self) -> Column:
        return PointColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class LineColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="LINE", python_type=str, **kwargs)


class LineDescriptor(ColumnDescriptor):
    column_class = LineColumn

    def _make_column(self) -> Column:
        return LineColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class LsegColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="LSEG", python_type=str, **kwargs)


class LsegDescriptor(ColumnDescriptor):
    column_class = LsegColumn

    def _make_column(self) -> Column:
        return LsegColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class BoxColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="BOX", python_type=str, **kwargs)


class BoxDescriptor(ColumnDescriptor):
    column_class = BoxColumn

    def _make_column(self) -> Column:
        return BoxColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class PathColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="PATH", python_type=str, **kwargs)


class PathDescriptor(ColumnDescriptor):
    column_class = PathColumn

    def _make_column(self) -> Column:
        return PathColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class PolygonColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="POLYGON", python_type=str, **kwargs)


class PolygonDescriptor(ColumnDescriptor):
    column_class = PolygonColumn

    def _make_column(self) -> Column:
        return PolygonColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class CircleColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="CIRCLE", python_type=str, **kwargs)


class CircleDescriptor(ColumnDescriptor):
    column_class = CircleColumn

    def _make_column(self) -> Column:
        return CircleColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )
