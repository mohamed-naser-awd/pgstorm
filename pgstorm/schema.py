"""
Models, PostgreSQL column types, and annotation helpers for table definitions.

A single ``from pgstorm import schema`` (or ``import pgstorm.schema as schema``) covers:

- :class:`~pgstorm.models.BaseModel`
- Scalar column classes (canonical names only)
- ``typing.Annotated`` and bracket metadata (:data:`IS_PRIMARY_KEY_FIELD`)
- Relation types and metadata (``ForeignKey``, ``ON_DELETE_*``, ``FK_FIELD``, ``Self``, …) —
  same objects as :mod:`pgstorm.types`
"""
from __future__ import annotations

from typing import Annotated

from pgstorm.types import (
    Field,
    ForeignKey,
    ManyToMany,
    OneToOne,
    Self,
    String,
    Varchar,
    FK_FIELD,
    FK_COLUMN,
    ReverseName,
    ReverseNameRef,
    ON_DELETE,
    ON_DELETE_RESTRICT,
    ON_DELETE_CASCADE,
    ON_DELETE_SET_NULL,
    ON_DELETE_NO_ACTION,
)

from pgstorm.models import BaseModel
from pgstorm.columns.base import (
    Column,
    FKColumnRef,
    FKFieldRef,
    IS_PRIMARY_KEY_FIELD,
    ScalarField,
)

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
from pgstorm.columns.character import BPChar, Char, Text
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
    "Annotated",
    "BaseModel",
    "BPChar",
    "BigInt",
    "BigSerial",
    "Bit",
    "Boolean",
    "Box",
    "Bytea",
    "Char",
    "Circle",
    "Cidr",
    "Column",
    "Date",
    "DoublePrecision",
    "FKColumnRef",
    "FK_FIELD",
    "FK_COLUMN",
    "FKFieldRef",
    "Field",
    "ForeignKey",
    "HalfVec",
    "IS_PRIMARY_KEY_FIELD",
    "Inet",
    "Integer",
    "Interval",
    "Json",
    "JsonPythonType",
    "Jsonb",
    "Line",
    "Lseg",
    "MacAddr",
    "MacAddr8",
    "ManyToMany",
    "Money",
    "Numeric",
    "ON_DELETE",
    "ON_DELETE_CASCADE",
    "ON_DELETE_NO_ACTION",
    "ON_DELETE_RESTRICT",
    "ON_DELETE_SET_NULL",
    "OneToOne",
    "Path",
    "PgLsn",
    "PgSnapshot",
    "Point",
    "Polygon",
    "Real",
    "ReverseName",
    "ReverseNameRef",
    "ScalarField",
    "Self",
    "Serial",
    "SmallInt",
    "SmallSerial",
    "SparseVec",
    "String",
    "Text",
    "Time",
    "TimeTZ",
    "Timestamp",
    "TimestampTZ",
    "TsQuery",
    "TsVector",
    "TxidSnapshot",
    "UUID",
    "VarBit",
    "Varchar",
    "Vector",
    "VectorBit",
    "Xml",
]
