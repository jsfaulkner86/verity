"""Structured logging with PHI-safe defaults.

Uses `structlog` for JSON-friendly structured events. The
`redact_processor` strips PHI from any string-valued log field before
the event is rendered, so callers cannot accidentally log raw prompts
or responses.
"""

from __future__ import annotations

import hashlib
import logging
import sys
from typing import Any

import structlog

from verity.config import get_settings
from verity.observability.phi import redact_phi


def _redact_processor(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Redact PHI from any string value in the event payload."""
    for key, value in list(event_dict.items()):
        if isinstance(value, str) and value:
            event_dict[key] = redact_phi(value)
    return event_dict


def hash_prompt(text: str) -> str:
    """Stable, short hash for correlation without revealing content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def configure_logging() -> None:
    """Configure root + structlog. Idempotent."""
    cfg = get_settings()
    level = getattr(logging, cfg.log_level, logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact_processor,
    ]
    if cfg.env == "development":
        processors.append(structlog.dev.ConsoleRenderer(colors=False))
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger. Auto-configures on first call."""
    if not structlog.is_configured():
        configure_logging()
    return structlog.get_logger(name) if name else structlog.get_logger()
