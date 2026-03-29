"""PostgreSQL geometric types: point, line, lseg, box, path, polygon, circle."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import ScalarField


class Point(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="POINT", python_type=str, **kwargs)


class Line(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="LINE", python_type=str, **kwargs)


class Lseg(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="LSEG", python_type=str, **kwargs)


class Box(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="BOX", python_type=str, **kwargs)


class Path(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="PATH", python_type=str, **kwargs)


class Polygon(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="POLYGON", python_type=str, **kwargs)


class Circle(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="CIRCLE", python_type=str, **kwargs)


PointColumn = PointDescriptor = Point
LineColumn = LineDescriptor = Line
LsegColumn = LsegDescriptor = Lseg
BoxColumn = BoxDescriptor = Box
PathColumn = PathDescriptor = Path
PolygonColumn = PolygonDescriptor = Polygon
CircleColumn = CircleDescriptor = Circle
