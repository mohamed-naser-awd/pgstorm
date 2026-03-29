"""
pgvector extension types: vector, halfvec, sparsevec, bit.
Requires the pgvector extension: CREATE EXTENSION vector;
"""
from __future__ import annotations

from typing import Any, Optional

from pgstorm.columns.base import ScalarField


class Vector(ScalarField):
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


class HalfVec(ScalarField):
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


class SparseVec(ScalarField):
    """pgvector sparsevec - sparse vector (non-zero elements)."""

    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="SPARSEVEC", python_type=dict, **kwargs)


class VectorBit(ScalarField):
    """pgvector bit(n) - binary vector for binary quantization (pgvector extension)."""

    def __init__(
        self,
        name: str = "",
        dimensions: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"BIT({dimensions})" if dimensions is not None else "BIT"
        super().__init__(name=name, pg_type=pg_type, python_type=list, **kwargs)
        self.dimensions = dimensions


VectorColumn = VectorDescriptor = Vector
HalfVecColumn = HalfVecDescriptor = HalfVec
SparseVecColumn = SparseVecDescriptor = SparseVec
VectorBitColumn = VectorBitDescriptor = VectorBit
