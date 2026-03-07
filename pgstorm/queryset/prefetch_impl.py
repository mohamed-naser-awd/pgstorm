"""
Implementation of prefetch_related logic.
"""
from __future__ import annotations

from typing import Any, Callable

from pgstorm.functions.expression import BoundColumnRef, Expression
from pgstorm.models import BaseModel
from pgstorm import operator as op

from pgstorm.queryset.parser import (
    _find_relation_between,
    _get_join_key_from_instance,
    _model_primary_key_field,
    compile_queryset,
)
from pgstorm.queryset.base import QuerySet


def _resolve_prefetch(
    prefetch: Any,
    main_model: type[BaseModel],
) -> tuple[type[BaseModel], QuerySet[Any], Any, Any, str, bool]:
    """
    Resolve a Prefetch into (prefetch_model, prefetch_qs, main_ref, prefetch_ref, as_attr, is_one_to_many).
    - main_ref: BoundColumnRef for the main model's column (for extracting key from main instances)
    - prefetch_ref: BoundColumnRef for the prefetch model's column (for filter and grouping)
    - is_one_to_many: True if each main gets a list, False if single object
    """
    from pgstorm.prefetch import Prefetch

    if not isinstance(prefetch, Prefetch):
        raise TypeError(f"Expected Prefetch, got {type(prefetch).__name__}")

    model_or_qs = prefetch.model_or_queryset
    if isinstance(model_or_qs, QuerySet):
        prefetch_model = model_or_qs.model
        prefetch_qs = model_or_qs.copy()
    elif isinstance(model_or_qs, type) and issubclass(model_or_qs, BaseModel):
        prefetch_model = model_or_qs
        prefetch_qs = model_or_qs.objects.copy()
    else:
        raise TypeError(
            f"Prefetch.model_or_queryset must be a model class or QuerySet, got {type(model_or_qs).__name__}"
        )

    main_pk = _model_primary_key_field(main_model)

    if prefetch.on is None:
        rel = _find_relation_between(main_model, prefetch_model)
        if rel is None:
            raise ValueError(
                f"No FK relation between {main_model.__name__} and {prefetch_model.__name__}. "
                "Provide explicit on= condition (e.g. UserProfile.user_id == Order.user_id)."
            )
        main_attr, target_attr, direction, reverse_name = rel
        if prefetch.as_attr is None:
            if reverse_name is None:
                raise ValueError(
                    f"as_attr is required when prefetching {prefetch_model.__name__}: "
                    "no reverse relation name available."
                )
            as_attr = reverse_name
        else:
            as_attr = prefetch.as_attr

        if direction == "main_to_target":
            main_ref = getattr(main_model, main_attr)
            if not isinstance(main_ref, BoundColumnRef):
                main_ref = main_ref.__get__(None, main_model)
            prefetch_ref = getattr(prefetch_model, target_attr)
            if not isinstance(prefetch_ref, BoundColumnRef):
                prefetch_ref = prefetch_ref.__get__(None, prefetch_model)
            is_one_to_many = False
        else:
            main_ref = getattr(main_model, main_pk)
            if not isinstance(main_ref, BoundColumnRef):
                main_ref = main_ref.__get__(None, main_model)
            prefetch_ref = getattr(prefetch_model, target_attr)
            if not isinstance(prefetch_ref, BoundColumnRef):
                prefetch_ref = prefetch_ref.__get__(None, prefetch_model)
            is_one_to_many = True
    else:
        on = prefetch.on
        if not isinstance(on, Expression) or on.operator not in (op.EQ, "="):
            raise ValueError(
                "Prefetch on= must be an equality Expression (e.g. UserProfile.user_id == Order.user_id)"
            )
        lhs, rhs = on.lhs, on.rhs
        if not isinstance(lhs, BoundColumnRef) or not isinstance(rhs, BoundColumnRef):
            raise ValueError(
                "Prefetch on= must use BoundColumnRef on both sides (e.g. UserProfile.user_id == Order.user_id)"
            )
        if lhs.model is prefetch_model and rhs.model is main_model:
            prefetch_ref, main_ref = lhs, rhs
        elif rhs.model is prefetch_model and lhs.model is main_model:
            prefetch_ref, main_ref = rhs, lhs
        else:
            raise ValueError(
                f"Prefetch on= must reference {main_model.__name__} (main) and {prefetch_model.__name__} (prefetch)"
            )
        if prefetch.as_attr is None:
            raise ValueError(
                f"as_attr is required when using custom on= (no FK between {main_model.__name__} and {prefetch_model.__name__})"
            )
        as_attr = prefetch.as_attr
        is_one_to_many = main_ref.attr_name == main_pk or (
            getattr(main_ref, "relation_attr", None) == main_pk
        )

    return prefetch_model, prefetch_qs, main_ref, prefetch_ref, as_attr, is_one_to_many


def _do_prefetch_sync(
    instances: list[Any],
    prefetches: list[Any],
    main_model: type[BaseModel],
    execute_fn: Callable[[Any], list[dict[str, Any]]],
    schema: str | None = None,
) -> None:
    """Run prefetch synchronously and attach results to instances."""
    if not instances or not prefetches:
        return

    for prefetch in prefetches:
        (
            prefetch_model,
            prefetch_qs,
            main_ref,
            prefetch_ref,
            as_attr,
            is_one_to_many,
        ) = _resolve_prefetch(prefetch, main_model)

        keys = []
        for obj in instances:
            k = _get_join_key_from_instance(obj, main_ref)
            if k is not None:
                keys.append(k)
        keys = list(dict.fromkeys(keys))
        if not keys:
            for obj in instances:
                setattr(obj, as_attr, [] if is_one_to_many else None)
            continue

        if schema is not None and not isinstance(prefetch.model_or_queryset, QuerySet):
            prefetch_qs = prefetch_qs.using_schema(schema)
        prefetch_qs = prefetch_qs.filter(
            Expression(prefetch_ref, op.IN, keys)
        )
        compiled = compile_queryset(prefetch_qs)
        rows = execute_fn(compiled)
        prefetched = prefetch_qs._rows_to_instances_sync(rows)

        grouped: dict[Any, list[Any]] = {}
        for obj in prefetched:
            k = _get_join_key_from_instance(obj, prefetch_ref)
            if k is not None:
                grouped.setdefault(k, []).append(obj)

        for obj in instances:
            k = _get_join_key_from_instance(obj, main_ref)
            objs = grouped.get(k, [])
            if is_one_to_many:
                setattr(obj, as_attr, objs)
            else:
                setattr(obj, as_attr, objs[0] if objs else None)


async def _do_prefetch_async(
    instances: list[Any],
    prefetches: list[Any],
    main_model: type[BaseModel],
    execute_fn: Callable[[Any], Any],
    schema: str | None = None,
) -> None:
    """Run prefetch asynchronously and attach results to instances."""
    if not instances or not prefetches:
        return

    for prefetch in prefetches:
        (
            prefetch_model,
            prefetch_qs,
            main_ref,
            prefetch_ref,
            as_attr,
            is_one_to_many,
        ) = _resolve_prefetch(prefetch, main_model)

        keys = []
        for obj in instances:
            k = _get_join_key_from_instance(obj, main_ref)
            if k is not None:
                keys.append(k)
        keys = list(dict.fromkeys(keys))
        if not keys:
            for obj in instances:
                setattr(obj, as_attr, [] if is_one_to_many else None)
            continue

        if schema is not None and not isinstance(prefetch.model_or_queryset, QuerySet):
            prefetch_qs = prefetch_qs.using_schema(schema)
        prefetch_qs = prefetch_qs.filter(
            Expression(prefetch_ref, op.IN, keys)
        )
        compiled = compile_queryset(prefetch_qs)
        rows = await execute_fn(compiled)
        prefetched = prefetch_qs._rows_to_instances_sync(rows)

        grouped: dict[Any, list[Any]] = {}
        for obj in prefetched:
            k = _get_join_key_from_instance(obj, prefetch_ref)
            if k is not None:
                grouped.setdefault(k, []).append(obj)

        for obj in instances:
            k = _get_join_key_from_instance(obj, main_ref)
            objs = grouped.get(k, [])
            if is_one_to_many:
                setattr(obj, as_attr, objs)
            else:
                setattr(obj, as_attr, objs[0] if objs else None)
