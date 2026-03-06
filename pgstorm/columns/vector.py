"""
pgvector extension types: vector, halfvec, sparsevec, bit.
Requires the pgvector extension: CREATE EXTENSION vector;
"""
from __future__ import annotations

from typing import Any, List, Optional

from pgstorm.columns.base import Column, ColumnDescriptor


class VectorColumn(Column):
    """pgvector vector(n) - 32-bit float vector with n dimensions."""

    def __init__(
        self,
        name: str = "",
        dimensions: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"VECTOR({dimensions})" if dimensions is not None else "VECTOR"
        super().__init__(name=name, pg_type=pg_type, python_type=list, **kwargs)
        self.dimensions = dimensions


class VectorDescriptor(ColumnDescriptor):
    column_class = VectorColumn

    def __init__(self, dimensions: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._dimensions = dimensions

    def _make_column(self) -> Column:
        return VectorColumn(
            dimensions=self._dimensions,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class HalfVecColumn(Column):
    """pgvector halfvec(n) - 16-bit float vector with n dimensions."""

    def __init__(
        self,
        name: str = "",
        dimensions: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"HALFVEC({dimensions})" if dimensions is not None else "HALFVEC"
        super().__init__(name=name, pg_type=pg_type, python_type=list, **kwargs)
        self.dimensions = dimensions


class HalfVecDescriptor(ColumnDescriptor):
    column_class = HalfVecColumn

    def __init__(self, dimensions: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._dimensions = dimensions

    def _make_column(self) -> Column:
        return HalfVecColumn(
            dimensions=self._dimensions,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class SparseVecColumn(Column):
    """pgvector sparsevec - sparse vector (non-zero elements)."""

    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="SPARSEVEC", python_type=dict, **kwargs)


class SparseVecDescriptor(ColumnDescriptor):
    column_class = SparseVecColumn

    def _make_column(self) -> Column:
        return SparseVecColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class VectorBitColumn(Column):
    """pgvector bit(n) - binary vector for binary quantization (pgvector extension)."""

    def __init__(
        self,
        name: str = "",
        dimensions: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        # pgvector bit type: bit(n) with n dimensions (up to 64000)
        pg_type = f"BIT({dimensions})" if dimensions is not None else "BIT"
        super().__init__(name=name, pg_type=pg_type, python_type=list, **kwargs)
        self.dimensions = dimensions


class VectorBitDescriptor(ColumnDescriptor):
    column_class = VectorBitColumn

    def __init__(self, dimensions: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._dimensions = dimensions

    def _make_column(self) -> Column:
        return VectorBitColumn(
            dimensions=self._dimensions,
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )
