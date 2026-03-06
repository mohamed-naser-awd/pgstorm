"""
pgstorm columns: descriptors and column classes for all PostgreSQL types.
Each type provides a Descriptor (for model attributes) and a Column (for DDL/ORM).
Descriptor API: get_pg_type() for migrations, get_column() for the Column instance.
"""
from pgstorm.columns.base import Column, ColumnDescriptor
from pgstorm.columns.numeric import (
    BigIntColumn,
    BigIntDescriptor,
    BigSerialColumn,
    BigSerialDescriptor,
    DecimalDescriptor,
    DecimalColumn,
    DoublePrecisionColumn,
    DoublePrecisionDescriptor,
    IntegerColumn,
    IntegerDescriptor,
    NumericColumn,
    NumericDescriptor,
    RealColumn,
    RealDescriptor,
    SerialColumn,
    SerialDescriptor,
    SmallIntColumn,
    SmallIntDescriptor,
    SmallSerialColumn,
    SmallSerialDescriptor,
)

from pgstorm.columns.character import (
    BPCharColumn,
    BPCharDescriptor,
    CharColumn,
    CharDescriptor,
    TextColumn,
    TextDescriptor,
    VarcharColumn,
    VarcharDescriptor,
)

from pgstorm.columns.binary import ByteaColumn, ByteaDescriptor
from pgstorm.columns.boolean import BooleanColumn, BooleanDescriptor
from pgstorm.columns.datetime import (
    DateColumn,
    DateDescriptor,
    IntervalColumn,
    IntervalDescriptor,
    TimeColumn,
    TimeDescriptor,
    TimeTZColumn,
    TimeTZDescriptor,
    TimestampColumn,
    TimestampDescriptor,
    TimestampTZColumn,
    TimestampTZDescriptor,
)

from pgstorm.columns.network import (
    CidrColumn,
    CidrDescriptor,
    InetColumn,
    InetDescriptor,
    MacAddrColumn,
    MacAddrDescriptor,
    MacAddr8Column,
    MacAddr8Descriptor,
)

from pgstorm.columns.bit import (
    BitColumn,
    BitDescriptor,
    VarBitColumn,
    VarBitDescriptor,
)

from pgstorm.columns.money import MoneyColumn, MoneyDescriptor
from pgstorm.columns.json_types import (
    JsonColumn,
    JsonDescriptor,
    JsonbColumn,
    JsonbDescriptor,
)

from pgstorm.columns.uuid_type import UUIDColumn, UUIDDescriptor
from pgstorm.columns.xml_type import XmlColumn, XmlDescriptor
from pgstorm.columns.geometric import (
    BoxColumn,
    BoxDescriptor,
    CircleColumn,
    CircleDescriptor,
    LineColumn,
    LineDescriptor,
    LsegColumn,
    LsegDescriptor,
    PathColumn,
    PathDescriptor,
    PointColumn,
    PointDescriptor,
    PolygonColumn,
    PolygonDescriptor,
)

from pgstorm.columns.textsearch import (
    TsQueryColumn,
    TsQueryDescriptor,
    TsVectorColumn,
    TsVectorDescriptor,
)

from pgstorm.columns.snapshot import (
    PgLsnColumn,
    PgLsnDescriptor,
    PgSnapshotColumn,
    PgSnapshotDescriptor,
    TxidSnapshotColumn,
    TxidSnapshotDescriptor,
)

from pgstorm.columns.vector import (
    HalfVecColumn,
    HalfVecDescriptor,
    SparseVecColumn,
    SparseVecDescriptor,
    VectorBitColumn,
    VectorBitDescriptor,
    VectorColumn,
    VectorDescriptor,
)

__all__ = [
    # Base
    "Column",
    "ColumnDescriptor",
    # Numeric
    "SmallIntColumn",
    "SmallIntDescriptor",
    "IntegerColumn",
    "IntegerDescriptor",
    "BigIntColumn",
    "BigIntDescriptor",
    "SmallSerialColumn",
    "SmallSerialDescriptor",
    "SerialColumn",
    "SerialDescriptor",
    "BigSerialColumn",
    "BigSerialDescriptor",
    "RealColumn",
    "RealDescriptor",
    "DoublePrecisionColumn",
    "DoublePrecisionDescriptor",
    "NumericColumn",
    "NumericDescriptor",
    "DecimalColumn",
    "DecimalDescriptor",
    # Character
    "TextColumn",
    "TextDescriptor",
    "CharColumn",
    "CharDescriptor",
    "VarcharColumn",
    "VarcharDescriptor",
    "BPCharColumn",
    "BPCharDescriptor",
    # Binary
    "ByteaColumn",
    "ByteaDescriptor",
    # Boolean
    "BooleanColumn",
    "BooleanDescriptor",
    # Date/Time
    "DateColumn",
    "DateDescriptor",
    "TimeColumn",
    "TimeDescriptor",
    "TimeTZColumn",
    "TimeTZDescriptor",
    "TimestampColumn",
    "TimestampDescriptor",
    "TimestampTZColumn",
    "TimestampTZDescriptor",
    "IntervalColumn",
    "IntervalDescriptor",
    # Network
    "InetColumn",
    "InetDescriptor",
    "CidrColumn",
    "CidrDescriptor",
    "MacAddrColumn",
    "MacAddrDescriptor",
    "MacAddr8Column",
    "MacAddr8Descriptor",
    # Bit
    "BitColumn",
    "BitDescriptor",
    "VarBitColumn",
    "VarBitDescriptor",
    # Money
    "MoneyColumn",
    "MoneyDescriptor",
    # JSON
    "JsonColumn",
    "JsonDescriptor",
    "JsonbColumn",
    "JsonbDescriptor",
    # UUID
    "UUIDColumn",
    "UUIDDescriptor",
    # XML
    "XmlColumn",
    "XmlDescriptor",
    # Geometric
    "PointColumn",
    "PointDescriptor",
    "LineColumn",
    "LineDescriptor",
    "LsegColumn",
    "LsegDescriptor",
    "BoxColumn",
    "BoxDescriptor",
    "PathColumn",
    "PathDescriptor",
    "PolygonColumn",
    "PolygonDescriptor",
    "CircleColumn",
    "CircleDescriptor",
    # Text search
    "TsVectorColumn",
    "TsVectorDescriptor",
    "TsQueryColumn",
    "TsQueryDescriptor",
    # Snapshot / LSN
    "PgLsnColumn",
    "PgLsnDescriptor",
    "PgSnapshotColumn",
    "PgSnapshotDescriptor",
    "TxidSnapshotColumn",
    "TxidSnapshotDescriptor",
    # pgvector
    "VectorColumn",
    "VectorDescriptor",
    "HalfVecColumn",
    "HalfVecDescriptor",
    "SparseVecColumn",
    "SparseVecDescriptor",
    "VectorBitColumn",
    "VectorBitDescriptor",
]
