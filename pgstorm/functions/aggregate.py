"""Aggregate functions for SQL: MIN, MAX, COUNT, SUM, AVG."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from pgstorm.functions.expression import BoundColumnRef


@dataclass(frozen=True, slots=True)
class Aggregate:
    """
    Represents a SQL aggregate function (MIN, MAX, COUNT, SUM, AVG).
    column is None for COUNT(*) which counts all rows.
    """

    func_name: str
    column: BoundColumnRef | None = None


def Min(column: BoundColumnRef) -> Aggregate:
    """Returns the smallest value of a column."""
    return Aggregate("MIN", column)


def Max(column: BoundColumnRef) -> Aggregate:
    """Returns the largest value of a column."""
    return Aggregate("MAX", column)


def Count(column: BoundColumnRef | None = None) -> Aggregate:
    """Returns the number of rows. Use Count() for COUNT(*), or Count(col) for COUNT(col)."""
    return Aggregate("COUNT", column)


def Sum(column: BoundColumnRef) -> Aggregate:
    """Returns the sum of a numerical column."""
    return Aggregate("SUM", column)


def Avg(column: BoundColumnRef) -> Aggregate:
    """Returns the average value of a numerical column."""
    return Aggregate("AVG", column)


def _default_alias_for_aggregate(agg: Aggregate) -> str:
    """Default alias for positional args: col_name_function_name. For COUNT(*), use 'count'."""
    func_lower = agg.func_name.lower()
    if agg.column is None:
        return func_lower
    col_name = agg.column.attr_name or ""
    if not col_name:
        return func_lower
    return f"{col_name}_{func_lower}"
