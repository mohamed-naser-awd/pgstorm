from pgstorm import BaseModel, BaseView, types
from pgstorm.functions.func import Now


class User(BaseModel):
    __table__ = "user"

    id: types.Integer[types.IS_PRIMARY_KEY_FIELD]
    email: types.String


class UserProfile(BaseModel):
    __table__ = "user_profile"
    user: types.ForeignKey[User, types.ON_DELETE_CASCADE]
    id: types.BigSerial[types.IS_PRIMARY_KEY_FIELD]


# Pre-defined queryset: inherits from User for columns, defines data via __queryset__
class ActiveUsers(BaseView, User):
    __table__ = "active_users"
    __queryset__ = lambda: User.objects  # or User.objects.filter(User.email.like("%@example.com"))
    __is_cte__ = True  # emit as WITH active_users AS (...)


# Temporary table with raw SQL (define columns explicitly)
class UserStats(BaseView):
    __table__ = "user_stats"
    __query__ = 'SELECT id, email, is_active FROM {schema}."user" LIMIT 10'
    __is_cte__ = True

    id: types.Integer
    email: types.String
    is_active: types.Integer


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

