"""
Temporary tables and pre-defined querysets.

These are table-like classes that define their data via a queryset or raw SQL,
instead of mapping to a physical table. They can inherit from another table
to reuse column definitions.

Use __queryset__ for a QuerySet, or __query__ for raw SQL.
Use __is_cte__ = True to emit the query as a CTE when used.
"""

from __future__ import annotations

from typing import Any, ClassVar, Self, TYPE_CHECKING

from pgstorm.models import BaseModel

if TYPE_CHECKING:
    from pgstorm.queryset.base import QuerySet


class BaseView(BaseModel):
    """
    Base for temporary tables and pre-defined querysets.

    Like a table definition but the data comes from a queryset or raw SQL instead
    of a physical table. Can inherit from another table to reuse columns.

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
