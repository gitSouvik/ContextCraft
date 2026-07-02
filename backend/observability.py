"""
Observability: structured JSON logs (so pipeline events are actually
queryable in a log aggregator instead of grep-only plaintext) and a small
set of Prometheus counters/histograms exposed at GET /metrics.

Kept dependency-light on purpose: `prometheus_client` is the one addition,
and the JSON formatter is ~20 lines of stdlib `logging` rather than pulling
in a full structured-logging framework for what this project needs.
"""
import json
import logging
import time
from contextlib import contextmanager
from typing import Iterator

from prometheus_client import Counter, Histogram

jobs_total = Counter("contextcraft_jobs_total", "Analyze jobs by terminal status", ["status"])
cache_lookups_total = Counter("contextcraft_cache_lookups_total", "Analysis cache lookups", ["result"])
gemini_calls_total = Counter("contextcraft_gemini_calls_total", "Gemini API calls by kind", ["kind"])
rate_limited_total = Counter("contextcraft_rate_limited_total", "Requests rejected by the rate limiter", ["route"])
pipeline_stage_seconds = Histogram(
    "contextcraft_pipeline_stage_seconds", "Wall time per pipeline stage", ["stage"]
)


@contextmanager
def timed_stage(stage: str) -> Iterator[None]:
    start = time.monotonic()
    try:
        yield
    finally:
        pipeline_stage_seconds.labels(stage=stage).observe(time.monotonic() - start)


class _JsonFormatter(logging.Formatter):
    RESERVED = set(logging.LogRecord(
        "", 0, "", 0, "", (), None
    ).__dict__.keys())

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extras = {k: v for k, v in record.__dict__.items() if k not in self.RESERVED}
        if extras:
            payload.update(extras)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)

    # These libraries log every HTTP call / git subprocess at INFO, which
    # drowns out the app's own pipeline events without adding much signal.
    for noisy in ("httpx", "httpcore", "urllib3", "git"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
