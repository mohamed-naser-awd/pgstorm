"""PostgreSQL character types: char, varchar, text, bpchar."""
from __future__ import annotations

from typing import Any, Optional

from pgstorm.columns.base import ScalarField


class _StringLookupsMixin:
    def _expr(self, operator: str, rhs: Any) -> Any:
        from pgstorm.functions.expression import Expression

        return Expression(self, operator, rhs)

    def like(self, pattern: str) -> Any:
        from pgstorm import operator as op

        return self._expr(op.LIKE, pattern)

    def ilike(self, pattern: str) -> Any:
        from pgstorm import operator as op

        return self._expr(op.ILIKE, pattern)


class Text(_StringLookupsMixin, ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="TEXT", python_type=str, **kwargs)


class Char(_StringLookupsMixin, ScalarField):
    def __init__(self, name: str = "", length: int = 1, **kwargs: Any) -> None:
        pg_type = f"CHAR({length})" if length else "CHAR(1)"
        super().__init__(name=name, pg_type=pg_type, python_type=str, **kwargs)
        self.length = length


class Varchar(_StringLookupsMixin, ScalarField):
    def __init__(
        self,
        name: str = "",
        length: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"VARCHAR({length})" if length is not None else "VARCHAR"
        super().__init__(name=name, pg_type=pg_type, python_type=str, **kwargs)
        self.length = length


class BPChar(_StringLookupsMixin, ScalarField):
    def __init__(
        self,
        name: str = "",
        length: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"BPCHAR({length})" if length is not None else "BPCHAR"
        super().__init__(name=name, pg_type=pg_type, python_type=str, **kwargs)
        self.length = length


TextColumn = TextDescriptor = Text
CharColumn = CharDescriptor = Char
VarcharColumn = VarcharDescriptor = Varchar
BPCharColumn = BPCharDescriptor = BPChar
