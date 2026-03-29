"""
Subquery/CTE views and pre-defined querysets (not PostgreSQL TEMPORARY tables).

For session-scoped ``CREATE TEMPORARY TABLE`` + ORM mapping, use :class:`pgstorm.models.BaseTempModel`
and :func:`pgstorm.compile_create_temp_table`.

These classes define their data via a queryset or raw SQL instead of a physical table.
They can inherit from another model to reuse column definitions.

Use ``__queryset__`` for a QuerySet, or ``__query__`` for raw SQL.
Use ``__is_cte__ = True`` to emit the query as a ``WITH`` CTE when used.
"""

from __future__ import annotations

from typing import Any, ClassVar, Self, TYPE_CHECKING

from pgstorm.models import BaseModel

if TYPE_CHECKING:
    from pgstorm.queryset.base import QuerySet


class BaseView(BaseModel):
    """
    Base for CTE/subquery-backed querysets (see module docstring).

    The data comes from a queryset or raw SQL instead of a physical table.
    Can inherit from another model to reuse columns.

    Define one of:
      - __queryset__: QuerySet or callable returning QuerySet (e.g. User.objects.filter(...))
      - __query__: Raw SQL string (e.g. "SELECT id, email FROM user WHERE active").
        Use {schema} placeholder to inject schema (e.g. 'SELECT * FROM {schema}."user"')

    Optional:
      - __is_cte__: If True, the query is emitted as a CTE (WITH name AS (...))
      - __table__: Alias/name for the subquery (default: class name lowercased)
      - __schema__: Schema for the underlying data (or use using_schema() when querying)
    """

    objects: ClassVar["QuerySet[Self]"]

    # Subclasses must define __queryset__ or __query__
    __queryset__: ClassVar["QuerySet[Self]"] | None = None
    __query__: ClassVar[str] | None = None
    __is_cte__: ClassVar[bool] = False
    __schema__: ClassVar[str] | None = None
