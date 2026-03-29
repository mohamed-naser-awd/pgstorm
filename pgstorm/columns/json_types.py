"""PostgreSQL JSON types: json, jsonb."""
from __future__ import annotations

from typing import Any, Dict, List, Union

from pgstorm.columns.base import ScalarField

# Python type for JSON: dict, list, str, int, float, bool, None
JsonPythonType = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


class Json(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="JSON", python_type=dict, **kwargs)


class Jsonb(ScalarField):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, pg_type="JSONB", python_type=dict, **kwargs)


JsonColumn = JsonDescriptor = Json
JsonbColumn = JsonbDescriptor = Jsonb
