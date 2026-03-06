"""PostgreSQL bit string types: bit(n), bit varying(n)."""
from __future__ import annotations

from typing import Any, Optional

from pgstorm.columns.base import Column, ColumnDescriptor


class BitColumn(Column):
    def __init__(
        self,
        name: str = "",
        length: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        # bit without length = bit(1)
        n = length if length is not None else 1
        pg_type = f"BIT({n})"
        super().__init__(name=name, pg_type=pg_type, python_type=str, **kwargs)
        self.length = n


class BitDescriptor(ColumnDescriptor):
    column_class = BitColumn

    def __init__(self, length: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._length = length

    def _make_column(self) -> Column:
        return BitColumn(
            length=self._length,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class VarBitColumn(Column):
    def __init__(
        self,
        name: str = "",
        length: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"BIT VARYING({length})" if length is not None else "BIT VARYING"
        super().__init__(name=name, pg_type=pg_type, python_type=str, **kwargs)
        self.length = length


class VarBitDescriptor(ColumnDescriptor):
    column_class = VarBitColumn

    def __init__(self, length: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._length = length

    def _make_column(self) -> Column:
        return VarBitColumn(
            length=self._length,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )
