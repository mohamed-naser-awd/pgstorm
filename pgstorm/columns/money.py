"""PostgreSQL monetary type: money."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import ScalarField


class Money(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="MONEY", python_type=str, **kwargs)


MoneyColumn = MoneyDescriptor = Money
