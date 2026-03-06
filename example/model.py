from pgstorm import BaseModel, types
from pgstorm.functions.func import Now


class User(BaseModel):
    __table__ = "user"

    id: types.Integer[types.IS_PRIMARY_KEY_FIELD]
    email: types.String


class UserProfile(BaseModel):
    __table__ = "user_profile"
    user: types.ForeignKey[User, types.ON_DELETE_CASCADE]


class AuditLog(BaseModel):
    """
    Audit log table. FK references tenant1.user - use using_schema("tenant1") when querying.
    Add CHECK (action IN ('INSERT', 'UPDATE', 'DELETE', 'SELECT')) in migration if needed.
    """
    __table__ = "audit_log"

    id: types.BigSerial[types.IS_PRIMARY_KEY_FIELD]
    user: types.ForeignKey[User]  # user_id -> tenant1.user(id)
    action: types.Varchar(20)  # CHECK in migration: INSERT, UPDATE, DELETE, SELECT
    target_table: types.Varchar(100)
    target_id: types.BigInt | None = None
    old_data: types.Jsonb | None = None
    new_data: types.Jsonb | None = None
    ip_address: types.Inet | None = None
    user_agent: types.String | None = None
    created_at: types.TimestampTZ(default=Now())

