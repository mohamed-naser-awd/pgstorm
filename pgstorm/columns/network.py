"""PostgreSQL network types: inet, cidr, macaddr, macaddr8."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import ScalarField


class Inet(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="INET", python_type=str, **kwargs)


class Cidr(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="CIDR", python_type=str, **kwargs)


class MacAddr(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="MACADDR", python_type=str, **kwargs)


class MacAddr8(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="MACADDR8", python_type=str, **kwargs)


InetColumn = InetDescriptor = Inet
CidrColumn = CidrDescriptor = Cidr
MacAddrColumn = MacAddrDescriptor = MacAddr
MacAddr8Column = MacAddr8Descriptor = MacAddr8
