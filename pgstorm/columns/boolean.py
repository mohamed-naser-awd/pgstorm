"""PostgreSQL boolean type."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import ScalarField


class Boolean(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="BOOLEAN", python_type=bool, **kwargs)


BooleanColumn = BooleanDescriptor = Boolean
