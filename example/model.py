"""
Example models: physical tables, foreign keys, self-FK, views/CTEs, and temporary tables.

Temporary data in PostgreSQL (two patterns):

1. **CTE (one statement)** — ``BaseView`` with ``__is_cte__ = True``. The subquery lives in a
   ``WITH name AS (...)`` clause for a single compiled SELECT. See ``ActiveUsers`` and ``UserStats``.

2. **TEMP table (session/connection)** — Subclass ``BaseTempModel`` (or set ``__temporary__ = True``),
   create the DDL with ``compile_create_temp_table(Model)`` and ``engine.execute``, then insert and
   query with ``Model.objects.create`` / ``bulk_create`` / ``.filter(...)`` like any other model.
   Generated SQL never schema-qualifies temp tables (they live in ``pg_temp``). See ``UserSessionStaging``.
"""
from pgstorm import BaseModel, BaseTempModel, BaseView, compile_create_temp_table, types
from pgstorm.functions.func import Now


class User(BaseModel):
    __table__ = "user"

    id: types.Integer[types.IS_PRIMARY_KEY_FIELD]
    email: types.String


class UserProfile(BaseModel):
    __table__ = "user_profile"
    user: types.ForeignKey[User, types.ON_DELETE_CASCADE]
    id: types.BigSerial[types.IS_PRIMARY_KEY_FIELD]


class Order(BaseModel):
    __table__ = "order"

    id: types.BigSerial[types.IS_PRIMARY_KEY_FIELD]
    user: types.ForeignKey[User]


class Comment(BaseModel):
    __table__ = "comment"

    id: types.BigSerial[types.IS_PRIMARY_KEY_FIELD]
    reply_to: types.ForeignKey[types.Self]


# --- Statement-scoped: CTE via BaseView (__is_cte__ = True) ---


class ActiveUsers(BaseView, User):
    """WITH active_users AS (SELECT ... FROM "user") — exists only for that one SQL statement."""

    __table__ = "active_users"
    __queryset__ = lambda: User.objects  # or User.objects.filter(User.email.like("%@example.com"))
    __is_cte__ = True


class UserStats(BaseView):
    """CTE built from raw SQL; columns declared explicitly for typing/SELECT list."""

    __table__ = "user_stats"
    __query__ = 'SELECT id, email, is_active FROM {schema}."user" LIMIT 10'
    __is_cte__ = True

    id: types.Integer
    email: types.String
    is_active: types.Integer


# --- Session-scoped: PostgreSQL TEMPORARY TABLE (BaseTempModel + compile_create_temp_table) ---


class UserSessionStaging(BaseTempModel):
    """
    Maps to a ``TEMPORARY`` table on the current session connection.

    Example (sync engine)::

        from pgstorm import engine, transaction

        with transaction():
            engine.execute(compile_create_temp_table(UserSessionStaging, on_commit="PRESERVE ROWS"))
            UserSessionStaging.objects.bulk_create(
                [
                    UserSessionStaging(user_id=u.id, score=0)
                    for u in User.objects.all().limit(100)
                ]
            )
            rows = list(UserSessionStaging.objects.all())

    Use ``UserSessionStaging.objects.create(...)`` for a single row. Inserts use the same
    ``.create()`` / ``.bulk_create()`` path as regular models; compiled SQL
    targets an unqualified temp table name (no schema prefix).

    ``using_schema(...)`` on the queryset does not prefix temp table names—PostgreSQL resolves
    unqualified identifiers to ``pg_temp`` for the session.
    """

    __table__ = "user_session_staging"

    user_id: types.BigInt
    score: types.Integer


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

