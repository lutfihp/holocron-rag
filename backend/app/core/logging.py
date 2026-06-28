"""structlog configuration for HOLOCRON backend.

Two modes controlled by `HOLOCRON_LOG_PRETTY`:
  - unset / false: JSONRenderer (prod, eval, demo recording).
  - true: ConsoleRenderer (local dev — human-readable).

`correlation_id` is bound by `app.main.correlation_id_middleware` via
`structlog.contextvars`. Every log record inside an HTTP request automatically
carries the request's correlation_id, so one id grep gives the full timeline.

uvicorn access logs stay default; this configures only the application logger.
"""
from __future__ import annotations

import logging
import sys

import structlog


class _LazyStdoutLogger:
    """Resolves sys.stdout at write-time, not configure-time.

    Necessary because pytest's capsys fixture swaps sys.stdout per test; if the
    factory captures the reference at configure time, later tests get a closed
    handle and structlog emits raise ValueError: I/O operation on closed file.
    """

    def _emit(self, message: str) -> None:
        print(message, file=sys.stdout, flush=True)

    msg = log = info = warning = error = critical = debug = _emit


class _LazyStdoutLoggerFactory:
    def __call__(self, *args, **kwargs) -> _LazyStdoutLogger:  # noqa: D401
        return _LazyStdoutLogger()


def configure_logging(*, pretty: bool) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
    ]
    renderer = (
        structlog.dev.ConsoleRenderer(colors=False)
        if pretty
        else structlog.processors.JSONRenderer()
    )
    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=_LazyStdoutLoggerFactory(),
        cache_logger_on_first_use=False,
    )
