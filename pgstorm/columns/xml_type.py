"""PostgreSQL XML type."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import ScalarField


class Xml(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="XML", python_type=str, **kwargs)


XmlColumn = XmlDescriptor = Xml
