"""Observer execution helpers for engine execute flow. Separates observer logic from execute()."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pgstorm.observers import (
    ObserverContext,
    _QUERY_ACTION_TO_POST,
    _QUERY_ACTION_TO_PRE,
    notify,
    notify_async,
    POST_SAVE,
    PRE_SAVE,
    QUERY_AFTER_EXECUTE,
    QUERY_BEFORE_EXECUTE,
)

if TYPE_CHECKING:
    from pgstorm.queryset.parser import CompiledQuery, RawQuery

# Query actions that trigger pre_save/post_save (Django-style: save = create or update)
_SAVE_ACTIONS = frozenset({"create", "bulk_create", "update", "bulk_update"})

# Actions without pre/post (fire same action in both before and after)
_LEGACY_ACTIONS = frozenset({"fetch", "raw_sql"})


def _make_ctx(compiled: "CompiledQuery | RawQuery", action: str, result: Any = None) -> ObserverContext:
    model = getattr(compiled, "model", None)
    table = getattr(compiled, "table", None)
    params = getattr(compiled, "params", [])
    extra = getattr(compiled, "extra", None) or {}
    return ObserverContext(
        action=action,
        model=model,
        table=table,
        compiled=compiled,
        params=params,
        result=result,
        extra=extra,
    )


def run_before_execute(compiled: "CompiledQuery | RawQuery") -> None:
    """Notify QUERY_BEFORE_EXECUTE and pre_* observers (before DB call)."""
    action = getattr(compiled, "action", "query")
    model = getattr(compiled, "model", None)
    table = getattr(compiled, "table", None)
    params = getattr(compiled, "params", [])
    extra = getattr(compiled, "extra", None) or {}

    ctx_before = ObserverContext(
        action=QUERY_BEFORE_EXECUTE,
        model=model,
        table=table,
        compiled=compiled,
        params=params,
        extra={"query_action": action, **extra},
    )
    notify(ctx_before)

    # Django-style pre_* actions
    if action in _QUERY_ACTION_TO_PRE:
        notify(_make_ctx(compiled, _QUERY_ACTION_TO_PRE[action]))
    if action in _SAVE_ACTIONS:
        notify(_make_ctx(compiled, PRE_SAVE))
    if action in _LEGACY_ACTIONS:
        notify(_make_ctx(compiled, action))


def run_after_execute(
    compiled: "CompiledQuery | RawQuery",
    result: Any,
) -> None:
    """Notify post_* and QUERY_AFTER_EXECUTE observers (after DB call)."""
    action = getattr(compiled, "action", "query")
    model = getattr(compiled, "model", None)
    table = getattr(compiled, "table", None)
    params = getattr(compiled, "params", [])
    extra = getattr(compiled, "extra", None) or {}

    # Django-style post_* actions
    if action in _QUERY_ACTION_TO_POST:
        notify(_make_ctx(compiled, _QUERY_ACTION_TO_POST[action], result))
    if action in _SAVE_ACTIONS:
        notify(_make_ctx(compiled, POST_SAVE, result))
    if action in _LEGACY_ACTIONS:
        notify(_make_ctx(compiled, action, result))

    ctx_after = ObserverContext(
        action=QUERY_AFTER_EXECUTE,
        model=model,
        table=table,
        compiled=compiled,
        params=params,
        result=result,
        extra={"query_action": action, **extra},
    )
    notify(ctx_after)


async def run_before_execute_async(compiled: "CompiledQuery | RawQuery") -> None:
    """Notify QUERY_BEFORE_EXECUTE and pre_* observers (async; awaits async callbacks)."""
    action = getattr(compiled, "action", "query")
    model = getattr(compiled, "model", None)
    table = getattr(compiled, "table", None)
    params = getattr(compiled, "params", [])
    extra = getattr(compiled, "extra", None) or {}

    ctx_before = ObserverContext(
        action=QUERY_BEFORE_EXECUTE,
        model=model,
        table=table,
        compiled=compiled,
        params=params,
        extra={"query_action": action, **extra},
    )
    await notify_async(ctx_before)

    if action in _QUERY_ACTION_TO_PRE:
        await notify_async(_make_ctx(compiled, _QUERY_ACTION_TO_PRE[action]))
    if action in _SAVE_ACTIONS:
        await notify_async(_make_ctx(compiled, PRE_SAVE))
    if action in _LEGACY_ACTIONS:
        await notify_async(_make_ctx(compiled, action))


async def run_after_execute_async(
    compiled: "CompiledQuery | RawQuery",
    result: Any,
) -> None:
    """Notify post_* and QUERY_AFTER_EXECUTE observers (async; awaits async callbacks)."""
    action = getattr(compiled, "action", "query")
    model = getattr(compiled, "model", None)
    table = getattr(compiled, "table", None)
    params = getattr(compiled, "params", [])
    extra = getattr(compiled, "extra", None) or {}

    if action in _QUERY_ACTION_TO_POST:
        await notify_async(_make_ctx(compiled, _QUERY_ACTION_TO_POST[action], result))
    if action in _SAVE_ACTIONS:
        await notify_async(_make_ctx(compiled, POST_SAVE, result))
    if action in _LEGACY_ACTIONS:
        await notify_async(_make_ctx(compiled, action, result))

    ctx_after = ObserverContext(
        action=QUERY_AFTER_EXECUTE,
        model=model,
        table=table,
        compiled=compiled,
        params=params,
        result=result,
        extra={"query_action": action, **extra},
    )
    await notify_async(ctx_after)
