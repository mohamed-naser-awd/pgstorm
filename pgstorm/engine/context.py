"""Context variable for the current engine instance."""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pgstorm.engine.base import BaseEngine

# Context var for the current engine. Set by create_engine().
engine: ContextVar["BaseEngine | None"] = ContextVar("pgstorm_engine", default=None)
