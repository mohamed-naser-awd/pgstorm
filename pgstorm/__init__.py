from pgstorm.models import BaseModel
from pgstorm.views import BaseView
from pgstorm import types
from pgstorm.prefetch import Prefetch
from pgstorm.observers import ObserverContext, observers, table_observers
from pgstorm.functions.expression import Q, and_, or_, not_, OuterRef, Subquery, F, Value
from pgstorm.functions.aggregate import Min, Max, Count, Sum, Avg
from pgstorm.functions.func import (
    Concat,
    Coalesce,
    Upper,
    Lower,
    Length,
    Trim,
    Replace,
    NullIf,
    Abs,
    Round,
    Floor,
    Ceil,
    Now,
    CurrentDate,
    CurrentTimestamp,
    DateTrunc,
    Func_,
)
from pgstorm.engine import engine, create_engine, transaction, set_search_path

def query(model: type[BaseModel]):
    """Return Model.objects for the given model. Alias for model.objects."""
    return model.objects


__all__ = [
    "BaseModel",
    "Prefetch",
    "query",
    "ObserverContext",
    "observers",
    "table_observers",
    "BaseView",
    "types",
    "Q",
    "and_",
    "or_",
    "not_",
    "OuterRef",
    "Subquery",
    "F",
    "Value",
    "Min",
    "Max",
    "Count",
    "Sum",
    "Avg",
    "Concat",
    "Coalesce",
    "Upper",
    "Lower",
    "Length",
    "Trim",
    "Replace",
    "NullIf",
    "Abs",
    "Round",
    "Floor",
    "Ceil",
    "Now",
    "CurrentDate",
    "CurrentTimestamp",
    "DateTrunc",
    "Func_",
    "engine",
    "create_engine",
    "transaction",
    "set_search_path",
]
