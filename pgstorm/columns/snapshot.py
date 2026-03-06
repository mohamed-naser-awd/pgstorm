"""PostgreSQL snapshot and LSN types: pg_lsn, pg_snapshot, txid_snapshot."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import Column, ColumnDescriptor


class PgLsnColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="PG_LSN", python_type=str, **kwargs)


class PgLsnDescriptor(ColumnDescriptor):
    column_class = PgLsnColumn

    def _make_column(self) -> Column:
        return PgLsnColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class PgSnapshotColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="PG_SNAPSHOT", python_type=str, **kwargs)


class PgSnapshotDescriptor(ColumnDescriptor):
    column_class = PgSnapshotColumn

    def _make_column(self) -> Column:
        return PgSnapshotColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )


class TxidSnapshotColumn(Column):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="TXID_SNAPSHOT", python_type=str, **kwargs)


class TxidSnapshotDescriptor(ColumnDescriptor):
    column_class = TxidSnapshotColumn

    def _make_column(self) -> Column:
        return TxidSnapshotColumn(
            default=self._default,
            nullable=self._nullable,
            primary_key=self._primary_key,
            unique=self._unique,
            index=self._index,
            **self._kwargs,
        )
