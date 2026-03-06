"""PostgreSQL character types: char, varchar, text, bpchar."""
from __future__ import annotations

from typing import Any, Optional

from pgstorm.columns.base import Column, ColumnDescriptor


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


# --- Text (unlimited length) ---
class TextColumn(_StringLookupsMixin, Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="TEXT", python_type=str, **kwargs)


class TextDescriptor(ColumnDescriptor[str, TextColumn]):
    column_class = TextColumn

    def _make_column(self) -> Column:
        return TextColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- Char (fixed length n) ---
class CharColumn(_StringLookupsMixin, Column):
    def __init__(self, name: str = "", length: int = 1, **kwargs: Any) -> None:
        pg_type = f"CHAR({length})" if length else "CHAR(1)"
        super().__init__(name=name, pg_type=pg_type, python_type=str, **kwargs)
        self.length = length


class CharDescriptor(ColumnDescriptor[str, CharColumn]):
    column_class = CharColumn

    def __init__(self, length: int = 1, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._length = length

    def _make_column(self) -> Column:
        return CharColumn(
            length=self._length,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- Varchar (variable length with optional limit) ---
class VarcharColumn(_StringLookupsMixin, Column):
    def __init__(
        self,
        name: str = "",
        length: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"VARCHAR({length})" if length is not None else "VARCHAR"
        super().__init__(name=name, pg_type=pg_type, python_type=str, **kwargs)
        self.length = length


class VarcharDescriptor(ColumnDescriptor[str, VarcharColumn]):
    column_class = VarcharColumn

    def __init__(self, length: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._length = length

    def _make_column(self) -> Column:
        return VarcharColumn(
            length=self._length,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


# --- BPChar (blank-padded char, variable unlimited with blank-trimmed semantics) ---
class BPCharColumn(_StringLookupsMixin, Column):
    def __init__(
        self,
        name: str = "",
        length: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"BPCHAR({length})" if length is not None else "BPCHAR"
        super().__init__(name=name, pg_type=pg_type, python_type=str, **kwargs)
        self.length = length


class BPCharDescriptor(ColumnDescriptor[str, BPCharColumn]):
    column_class = BPCharColumn

    def __init__(self, length: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._length = length

    def _make_column(self) -> Column:
        return BPCharColumn(
            length=self._length,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )
