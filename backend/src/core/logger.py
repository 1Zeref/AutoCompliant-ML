"""
Structured JSON Logger with Correlation ID and Day-1 Observability.
Conforms to industry observability standards: timestamp, level, correlation_id, message.
"""
import json
import logging
import sys
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Any, Dict, Optional

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="system")


def get_correlation_id() -> str:
    return correlation_id_ctx.get()


def set_correlation_id(correlation_id: str) -> None:
    correlation_id_ctx.set(correlation_id)


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": getattr(record, "correlation_id", get_correlation_id()),
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_data.update(record.extra_data)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logger(name: str = "traffic_assistant", level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


logger = setup_logger()
