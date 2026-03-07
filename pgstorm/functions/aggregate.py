"""Aggregate functions for SQL: MIN, MAX, COUNT, SUM, AVG."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from pgstorm.functions.expression import BoundColumnRef
from pgstorm.functions.func import Func


@dataclass(frozen=True, slots=True)
class Aggregate:
    """
    Represents a SQL aggregate function (MIN, MAX, COUNT, SUM, AVG).
    column is None for COUNT(*) which counts all rows.
    column can be BoundColumnRef, str (attribute name), or Func (expression).
    """

    func_name: str
    column: BoundColumnRef | str | Func | None = None


def Min(column: Union[BoundColumnRef, str, Func]) -> Aggregate:
    """Returns the smallest value of a column or expression."""
    return Aggregate("MIN", column)


def Max(column: Union[BoundColumnRef, str, Func]) -> Aggregate:
    """Returns the largest value of a column or expression."""
    return Aggregate("MAX", column)


def Count(column: Union[BoundColumnRef, str, Func, None] = None) -> Aggregate:
    """Returns the number of rows. Use Count() for COUNT(*), or Count(col) for COUNT(col)."""
    return Aggregate("COUNT", column)


def Sum(column: Union[BoundColumnRef, str, Func]) -> Aggregate:
    """Returns the sum of a numerical column or expression."""
    return Aggregate("SUM", column)


def Avg(column: Union[BoundColumnRef, str, Func]) -> Aggregate:
    """Returns the average value of a numerical column or expression."""
    return Aggregate("AVG", column)


def _default_alias_for_aggregate(agg: Aggregate) -> str:
    """Default alias for positional args: col_name_function_name. For COUNT(*), use 'count'."""
    func_lower = agg.func_name.lower()
    if agg.column is None:
        return func_lower
    if isinstance(agg.column, str):
        return f"{agg.column}_{func_lower}" if agg.column else func_lower
    if isinstance(agg.column, Func):
        return f"{agg.column.func_name.lower()}_{func_lower}"
    col_name = agg.column.attr_name or ""
    if not col_name:
        return func_lower
    return f"{col_name}_{func_lower}"
