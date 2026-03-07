"""Abstract interface for database drivers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Union

from pgstorm.queryset.parser import CompiledQuery, RawQuery

CompiledOrRaw = Union[CompiledQuery, RawQuery]


class EngineInterface(ABC):
    """
    Abstract interface for database drivers.
    Implementations handle connection, execution, and transactions.
    """

    @property
    @abstractmethod
    def is_async(self) -> bool:
        """True if this interface returns coroutines from execute/transaction."""
        ...

    @abstractmethod
    def execute(self, compiled: "CompiledOrRaw") -> Any:
        """
        Execute a compiled query or raw SQL. Returns list of rows for SELECT,
        or empty list for DML. For async interfaces, returns a coroutine.
        """
        ...

    @abstractmethod
    def begin(self) -> Any:
        """Begin a transaction. For async, returns coroutine."""
        ...

    @abstractmethod
    def commit(self) -> Any:
        """Commit the current transaction. For async, returns coroutine."""
        ...

    @abstractmethod
    def rollback(self) -> Any:
        """Rollback the current transaction. For async, returns coroutine."""
        ...
