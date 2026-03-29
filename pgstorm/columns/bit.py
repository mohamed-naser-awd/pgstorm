"""PostgreSQL bit string types: bit(n), bit varying(n)."""
from __future__ import annotations

from typing import Any, Optional

from pgstorm.columns.base import ScalarField


class Bit(ScalarField):
    def __init__(
        self,
        name: str = "",
        length: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        n = length if length is not None else 1
        pg_type = f"BIT({n})"
        super().__init__(name=name, pg_type=pg_type, python_type=str, **kwargs)
        self.length = n


class VarBit(ScalarField):
    def __init__(
        self,
        name: str = "",
        length: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        pg_type = f"BIT VARYING({length})" if length is not None else "BIT VARYING"
        super().__init__(name=name, pg_type=pg_type, python_type=str, **kwargs)
        self.length = length


BitColumn = BitDescriptor = Bit
VarBitColumn = VarBitDescriptor = VarBit
