"""
Public type API for pgstorm models.
- Scalars: age: types.Integer, email: types.String.
- Relations: user: types.ForeignKey[User], or with metadata: types.ForeignKey[User, types.ON_DELETE_CASCADE, types.FK_FIELD("email")].
  Self-referential: reply_to: types.ForeignKey[types.Self]. Same pattern for OneToOne and ManyToMany.
"""
from __future__ import annotations

from typing import Annotated

from pgstorm.columns.base import FKColumnRef, FKFieldRef, Field, ForeignKey, IS_PRIMARY_KEY_FIELD, ManyToMany, OneToOne, ReverseNameRef, Self
from pgstorm.columns.character import TextDescriptor, VarcharDescriptor
from pgstorm.columns.datetime import TimestampTZDescriptor
from pgstorm.columns.json_types import JsonbDescriptor
from pgstorm.columns.network import InetDescriptor
from pgstorm.columns.numeric import BigIntDescriptor, BigSerialDescriptor, IntegerDescriptor

# Type classes (inherit from Field via *Descriptor -> ColumnDescriptor = Field)
Integer = IntegerDescriptor
String = TextDescriptor
BigSerial = BigSerialDescriptor
BigInt = BigIntDescriptor
Jsonb = JsonbDescriptor
Inet = InetDescriptor


def Varchar(length: int | None = None):
    """VARCHAR with optional length. Use: action: types.Varchar(20)"""
    return VarcharDescriptor(length=length)


def TimestampTZ(default=None, precision: int | None = None):
    """TIMESTAMP WITH TIME ZONE. Use: created_at: types.TimestampTZ(default=Now())"""
    return TimestampTZDescriptor(default=default, precision=precision)

# Relation types: metadata goes in the brackets, e.g. ForeignKey[User, ON_DELETE_CASCADE, FK_FIELD("email")]


def ON_DELETE(action: str) -> str:
    """Use inside relation type args: types.ForeignKey[User, types.ON_DELETE_CASCADE]."""
    return action


ON_DELETE_RESTRICT = ON_DELETE("RESTRICT")
ON_DELETE_CASCADE = ON_DELETE("CASCADE")
ON_DELETE_SET_NULL = ON_DELETE("SET NULL")
ON_DELETE_NO_ACTION = ON_DELETE("NO ACTION")


def FK_FIELD(field_name: str) -> FKFieldRef:
    """Use inside relation type args to specify which field on the target this FK references."""
    return FKFieldRef(field_name)


def FK_COLUMN(column_name: str) -> FKColumnRef:
    """Use inside relation type args to specify the DB column name (default: {attr}_id)."""
    return FKColumnRef(column_name)


def ReverseName(name: str) -> ReverseNameRef:
    """Use inside relation type args to set the reverse relation name on the target model."""
    return ReverseNameRef(name)


__all__ = [
    "Annotated",
    "BigInt",
    "BigSerial",
    "Field",
    "FK_COLUMN",
    "FK_FIELD",
    "ForeignKey",
    "Inet",
    "Integer",
    "IS_PRIMARY_KEY_FIELD",
    "Jsonb",
    "ManyToMany",
    "OneToOne",
    "ON_DELETE",
    "ON_DELETE_RESTRICT",
    "ON_DELETE_CASCADE",
    "ON_DELETE_SET_NULL",
    "ON_DELETE_NO_ACTION",
    "ReverseName",
    "ReverseNameRef",
    "Self",
    "String",
    "TimestampTZ",
    "Varchar",
]
