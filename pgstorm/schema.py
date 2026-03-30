"""
Models and PostgreSQL column types for table definitions.

Re-exports :class:`~pgstorm.models.BaseModel` so a single ``import pgstorm.schema as schema``
(or ``from pgstorm import schema``) is enough for scalar columns and model base class.

Also exports scalar column classes (:class:`~pgstorm.columns.base.ScalarField` subclasses) and
:class:`~pgstorm.columns.base.Column` under canonical names only (no legacy ``*Descriptor`` /
``*Column`` aliases).

Relation fields (``ForeignKey``, etc.) and ``types`` conveniences still come from
``pgstorm.types`` or ``pgstorm.columns.base``.
"""
from __future__ import annotations

from pgstorm.models import BaseModel
from pgstorm.columns.base import Column, ScalarField

from pgstorm.columns.numeric import (
    BigInt,
    BigSerial,
    DoublePrecision,
    Integer,
    Numeric,
    Real,
    Serial,
    SmallInt,
    SmallSerial,
)
from pgstorm.columns.character import BPChar, Char, Text, Varchar
from pgstorm.columns.binary import Bytea
from pgstorm.columns.boolean import Boolean
from pgstorm.columns.datetime import (
    Date,
    Interval,
    Time,
    TimeTZ,
    Timestamp,
    TimestampTZ,
)
from pgstorm.columns.network import Cidr, Inet, MacAddr, MacAddr8
from pgstorm.columns.bit import Bit, VarBit
from pgstorm.columns.money import Money
from pgstorm.columns.json_types import Json, Jsonb, JsonPythonType
from pgstorm.columns.uuid_type import UUID
from pgstorm.columns.xml_type import Xml
from pgstorm.columns.geometric import Box, Circle, Line, Lseg, Path, Point, Polygon
from pgstorm.columns.textsearch import TsQuery, TsVector
from pgstorm.columns.snapshot import PgLsn, PgSnapshot, TxidSnapshot
from pgstorm.columns.vector import HalfVec, SparseVec, Vector, VectorBit

__all__ = [
    "BaseModel",
    "Column",
    "ScalarField",
    # Numeric
    "SmallInt",
    "Integer",
    "BigInt",
    "SmallSerial",
    "Serial",
    "BigSerial",
    "Real",
    "DoublePrecision",
    "Numeric",
    # Character & binary
    "Text",
    "Char",
    "Varchar",
    "BPChar",
    "Bytea",
    "Boolean",
    # Date/time
    "Date",
    "Time",
    "TimeTZ",
    "Timestamp",
    "TimestampTZ",
    "Interval",
    # Network
    "Inet",
    "Cidr",
    "MacAddr",
    "MacAddr8",
    # Bit
    "Bit",
    "VarBit",
    "Money",
    # JSON
    "Json",
    "Jsonb",
    "JsonPythonType",
    "UUID",
    "Xml",
    # Geometric
    "Point",
    "Line",
    "Lseg",
    "Box",
    "Path",
    "Polygon",
    "Circle",
    # Full text
    "TsVector",
    "TsQuery",
    # Snapshot / LSN
    "PgLsn",
    "PgSnapshot",
    "TxidSnapshot",
    # pgvector
    "Vector",
    "HalfVec",
    "SparseVec",
    "VectorBit",
]
