"""PostgreSQL network types: inet, cidr, macaddr, macaddr8."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import Column, ColumnDescriptor


# inet/cidr: Python type can be str or ipaddress.IPv4Address/IPv6Address/IPv4Network/IPv6Network
# We use str for simplicity; apps can use ipaddress module for parsing.


class InetColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="INET", python_type=str, **kwargs)


class InetDescriptor(ColumnDescriptor):
    column_class = InetColumn

    def _make_column(self) -> Column:
        return InetColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class CidrColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="CIDR", python_type=str, **kwargs)


class CidrDescriptor(ColumnDescriptor):
    column_class = CidrColumn

    def _make_column(self) -> Column:
        return CidrColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class MacAddrColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="MACADDR", python_type=str, **kwargs)


class MacAddrDescriptor(ColumnDescriptor):
    column_class = MacAddrColumn

    def _make_column(self) -> Column:
        return MacAddrColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class MacAddr8Column(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="MACADDR8", python_type=str, **kwargs)


class MacAddr8Descriptor(ColumnDescriptor):
    column_class = MacAddr8Column

    def _make_column(self) -> Column:
        return MacAddr8Column(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )
