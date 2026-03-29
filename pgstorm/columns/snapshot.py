"""PostgreSQL snapshot and LSN types: pg_lsn, txid_snapshot, pg_snapshot."""
from __future__ import annotations

from typing import Any

from pgstorm.columns.base import ScalarField


class PgLsn(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="PG_LSN", python_type=str, **kwargs)


class PgSnapshot(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="PG_SNAPSHOT", python_type=str, **kwargs)


class TxidSnapshot(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="TXID_SNAPSHOT", python_type=str, **kwargs)


PgLsnColumn = PgLsnDescriptor = PgLsn
PgSnapshotColumn = PgSnapshotDescriptor = PgSnapshot
TxidSnapshotColumn = TxidSnapshotDescriptor = TxidSnapshot
