"""
Shared exponential-backoff retry helper for every Gemini API call site
(guide generation, embeddings, chat). Pulled out once the project grew a
second and third caller — the free tier's tight RPM ceiling makes retry-on-429
a hard requirement everywhere, not just in the original guide-generation path.
"""
import time
from typing import Callable, Optional, TypeVar

T = TypeVar("T")

TRANSIENT_MARKERS = ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")


class TransientCallFailure(RuntimeError):
    """Raised when all retries are exhausted; wraps the last underlying error."""


def is_transient(error: Exception) -> bool:
    return any(marker in str(error) for marker in TRANSIENT_MARKERS)


def call_with_backoff(fn: Callable[[], T], max_retries: int = 4, base_delay: float = 1.0) -> T:
    """
    Calls `fn()`, retrying with exponential backoff (base_delay, 2x, 4x, ...)
    on transient errors (429 rate-limit, 503 overload). Non-transient errors
    propagate immediately without retrying.
    """
    delay = base_delay
    last_error: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1 and is_transient(e):
                time.sleep(delay)
                delay *= 2
                continue
            raise TransientCallFailure(str(e)) from e
    # Unreachable in practice (the loop always returns or raises), but keeps
    # type checkers happy without a `# type: ignore`.
    raise TransientCallFailure(str(last_error))
