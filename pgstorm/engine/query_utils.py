"""Utilities for converting psycopg Composable to driver-specific formats."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg.sql import Composable


def composable_to_plain(composable: "Composable", params: list) -> tuple[str, list]:
    """
    Convert a psycopg Composable to (query_string, params) with %s placeholders.
    Used by drivers that don't support Composable natively (psycopg2, asyncpg).
    """
    from psycopg import sql

    parts: list[str] = []
    param_idx = [0]

    def walk(obj: "Composable") -> None:
        if isinstance(obj, sql.SQL):
            parts.append(obj._obj)
        elif isinstance(obj, sql.Composed):
            for item in obj._obj:
                walk(item)
        elif isinstance(obj, sql.Identifier):
            parts.append(obj.as_string(None))
        elif isinstance(obj, sql.Placeholder):
            parts.append(obj.as_string(None))
            param_idx[0] += 1
        elif isinstance(obj, sql.Literal):
            parts.append(obj.as_string(None))
        else:
            parts.append(obj.as_string(None))

    walk(composable)
    return "".join(parts), list(params)


def to_asyncpg_format(query: str, params: list) -> tuple[str, list]:
    """
    Convert %s-style query to asyncpg $1, $2, ... format.
    """
    result: list[str] = []
    idx = 1
    i = 0
    while i < len(query):
        if query[i : i + 2] == "%s":
            result.append(f"${idx}")
            idx += 1
            i += 2
        else:
            result.append(query[i])
            i += 1
    return "".join(result), params
