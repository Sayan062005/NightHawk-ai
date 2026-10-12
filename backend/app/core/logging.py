"""NightHawk AI — Structured logging with secret redaction."""

from __future__ import annotations

import logging
import re
import sys

import structlog

# Patterns to redact from all log output
_REDACT_PATTERNS = [
    re.compile(r"(nvapi-)[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile(r"(sk-)[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[A-Za-z0-9._-]+", re.IGNORECASE),
    re.compile(r"(password[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+", re.IGNORECASE),
    re.compile(r"(token[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+", re.IGNORECASE),
    re.compile(r"(secret[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+", re.IGNORECASE),
    re.compile(r"(cookie[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+", re.IGNORECASE),
]


def _redact_secrets(_, __, event_dict: dict) -> dict:
    """Processor to redact secrets from log events."""
    for key, value in list(event_dict.items()):
        if isinstance(value, str):
            for pattern in _REDACT_PATTERNS:
                value = pattern.sub(r"\1[REDACTED]", value)
            event_dict[key] = value
    return event_dict


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure structured logging with secret redaction."""
    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _redact_secrets,
    ]

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)
