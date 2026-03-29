"""PostgreSQL full-text search types: tsvector, tsquery."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import ScalarField


class TsVector(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="TSVECTOR", python_type=str, **kwargs)


class TsQuery(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="TSQUERY", python_type=str, **kwargs)


TsVectorColumn = TsVectorDescriptor = TsVector
TsQueryColumn = TsQueryDescriptor = TsQuery
