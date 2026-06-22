"""Shared structured logging configuration.

Wraps ``structlog`` with sensible defaults for the project: JSON output
when stderr is a pipe (CI, production), human-readable ConsoleRenderer
when stderr is a TTY (local dev). Exports a single :func:`get_logger`
that returns a bound logger from the shared configuration.

Usage::

    from atlas.log import configure_logging, get_logger

    configure_logging()
    logger = get_logger()
    logger.info("Server started", port=8080)
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog once at application startup.

    Call this exactly once, early in ``main()``. The renderer switches
    automatically: JSON when stderr is a pipe, colourful console when
    stderr is a TTY.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if sys.stderr.isatty() else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level.upper())),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger() -> structlog.stdlib.BoundLogger:
    """Return a logger from the shared structlog configuration."""
    return structlog.get_logger()
