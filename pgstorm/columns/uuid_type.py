"""PostgreSQL UUID type."""
from __future__ import annotations

import uuid
from typing import Any

from pgstorm.columns.base import ScalarField


class UUID(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="UUID", python_type=uuid.UUID, **kwargs)

    def _expr(self, operator: str, rhs: Any) -> Any:
        from pgstorm.functions.expression import Expression

        return Expression(self, operator, rhs)

    def eq(self, rhs: Any) -> Any:
        from pgstorm import operator as op

        return self._expr(op.EQ, rhs)

    def ne(self, rhs: Any) -> Any:
        from pgstorm import operator as op

        return self._expr(op.NE, rhs)


UUIDColumn = UUIDDescriptor = UUID
