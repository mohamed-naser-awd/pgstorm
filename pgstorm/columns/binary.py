"""PostgreSQL binary type: bytea."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import ScalarField


class Bytea(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="BYTEA", python_type=bytes, **kwargs)


ByteaColumn = ByteaDescriptor = Bytea
