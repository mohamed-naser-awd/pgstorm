"""PostgreSQL function expressions for use in annotate(), alias(), and filters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union

from pgstorm.functions.expression import BoundColumnRef


@dataclass(frozen=True, slots=True)
class Func:
    """
    Represents a SQL function call: FUNC_NAME(arg1, arg2, ...).
    Args can be BoundColumnRef, Func, or literals (str, int, etc.).
    """

    func_name: str
    args: tuple[Any, ...]

    def __repr__(self) -> str:
        return f"Func({self.func_name!r}, {self.args!r})"


def _func(name: str, *args: Any) -> Func:
    return Func(name, args)


# --- String functions ---
def Concat(*args: Union[BoundColumnRef, Func, str]) -> Func:
    """PostgreSQL CONCAT(str1, str2, ...)."""
    return Func("CONCAT", args)


def Upper(expr: Union[BoundColumnRef, Func]) -> Func:
    """PostgreSQL UPPER(text)."""
    return Func("UPPER", (expr,))


def Lower(expr: Union[BoundColumnRef, Func]) -> Func:
    """PostgreSQL LOWER(text)."""
    return Func("LOWER", (expr,))


def Length(expr: Union[BoundColumnRef, Func]) -> Func:
    """PostgreSQL LENGTH(text)."""
    return Func("LENGTH", (expr,))


def Trim(expr: Union[BoundColumnRef, Func], chars: str | None = None) -> Func:
    """PostgreSQL TRIM([chars FROM] text)."""
    if chars is not None:
        return Func("TRIM", (expr, chars))
    return Func("TRIM", (expr,))


def LTrim(expr: Union[BoundColumnRef, Func], chars: str | None = None) -> Func:
    """PostgreSQL LTRIM(text [, chars])."""
    if chars is not None:
        return Func("LTRIM", (expr, chars))
    return Func("LTRIM", (expr,))


def RTrim(expr: Union[BoundColumnRef, Func], chars: str | None = None) -> Func:
    """PostgreSQL RTRIM(text [, chars])."""
    if chars is not None:
        return Func("RTRIM", (expr, chars))
    return Func("RTRIM", (expr,))


def Substring(expr: Union[BoundColumnRef, Func], start: int, length: int | None = None) -> Func:
    """PostgreSQL SUBSTRING(string FROM start [FOR length])."""
    if length is not None:
        return Func("SUBSTRING", (expr, start, length))
    return Func("SUBSTRING", (expr, start))


def Replace(expr: Union[BoundColumnRef, Func], from_str: str, to_str: str) -> Func:
    """PostgreSQL REPLACE(string, from, to)."""
    return Func("REPLACE", (expr, from_str, to_str))


# --- General / coalesce ---
def Coalesce(*args: Any) -> Func:
    """PostgreSQL COALESCE(val1, val2, ...). Returns first non-NULL."""
    return Func("COALESCE", args)


def NullIf(a: Any, b: Any) -> Func:
    """PostgreSQL NULLIF(a, b). Returns NULL if a=b."""
    return Func("NULLIF", (a, b))


# --- Math ---
def Abs(expr: Union[BoundColumnRef, Func]) -> Func:
    """PostgreSQL ABS(numeric)."""
    return Func("ABS", (expr,))


def Round(expr: Union[BoundColumnRef, Func], precision: int = 0) -> Func:
    """PostgreSQL ROUND(numeric [, precision])."""
    return Func("ROUND", (expr, precision))


def Floor(expr: Union[BoundColumnRef, Func]) -> Func:
    """PostgreSQL FLOOR(numeric)."""
    return Func("FLOOR", (expr,))


def Ceil(expr: Union[BoundColumnRef, Func]) -> Func:
    """PostgreSQL CEIL(numeric)."""
    return Func("CEIL", (expr,))


# --- Date/time ---
def Now() -> Func:
    """PostgreSQL NOW()."""
    return Func("NOW", ())


def CurrentDate() -> Func:
    """PostgreSQL CURRENT_DATE."""
    return Func("CURRENT_DATE", ())


def CurrentTimestamp() -> Func:
    """PostgreSQL CURRENT_TIMESTAMP."""
    return Func("CURRENT_TIMESTAMP", ())


def DateTrunc(field: str, expr: Union[BoundColumnRef, Func]) -> Func:
    """PostgreSQL DATE_TRUNC(field, timestamp)."""
    return Func("DATE_TRUNC", (field, expr))


# --- Generic for any PostgreSQL function ---
def Func_(name: str, *args: Any) -> Func:
    """Generic SQL function. Use for any PostgreSQL function not covered above."""
    return Func(name.upper(), args)
