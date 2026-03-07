"""
Prefetch related objects with flexible join conditions.

Supports prefetching related models via FK or arbitrary join conditions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from pgstorm.models import BaseModel

if TYPE_CHECKING:
    from pgstorm.queryset.base import QuerySet


@dataclass(frozen=True)
class Prefetch:
    """
    Describes a prefetch for prefetch_related().

    - model_or_queryset: The model class to prefetch, or a QuerySet (e.g. UserProfile.objects.filter(...))
    - on: Optional join condition (Expression). If None, uses FK between main and prefetch model (raises if no FK).
    - as_attr: Attribute name to set on each main object. If None, uses FK reverse name (raises if no FK).
    """

    model_or_queryset: type[BaseModel] | "QuerySet[Any]"
    on: Any | None = None  # Expression when provided
    as_attr: str | None = None
