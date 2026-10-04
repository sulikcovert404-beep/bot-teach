import sys
from collections.abc import Iterator
from typing import Any

import pytest

from app.core.rate_limit import InMemoryRateLimitMiddleware


def _in_memory_limiters(stack: Any) -> Iterator[InMemoryRateLimitMiddleware]:
    pending = [stack]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        if type(current) is InMemoryRateLimitMiddleware:
            yield current
        inner = getattr(current, "app", None)
        if inner is not None:
            pending.append(inner)


def _clear_shared_in_memory_limits() -> None:
    main_module = sys.modules.get("app.main")
    app = getattr(main_module, "app", None)
    if app is None:
        return
    for limiter in _in_memory_limiters(app.middleware_stack):
        limiter._windows.clear()


@pytest.fixture(autouse=True)
def isolate_shared_in_memory_rate_limit_state() -> Iterator[None]:
    """Keep singleton-app rate-limit state inside each test's own boundary."""
    _clear_shared_in_memory_limits()
    yield
    _clear_shared_in_memory_limits()
