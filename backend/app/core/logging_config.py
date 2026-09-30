"""Structured JSON and contextual logging infrastructure with Trace IDs."""
from __future__ import annotations
import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

# Global context variable for request / execution trace ID
current_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_trace_id", default="trace-system"
)


def get_current_trace_id() -> str:
    """Retrieve the active trace ID from the async context."""
    return current_trace_id.get()


def set_current_trace_id(trace_id: str) -> None:
    """Set the active trace ID for the async context."""
    current_trace_id.set(trace_id)


class StructuredLogFormatter(logging.Formatter):
    """Custom logging formatter injecting ISO timestamps and active trace IDs."""

    def __init__(self, json_output: bool = False):
        super().__init__()
        self.json_output = json_output

    def format(self, record: logging.LogRecord) -> str:
        trace_id = getattr(record, "trace_id", None) or get_current_trace_id()
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

        if self.json_output:
            log_obj = {
                "timestamp": timestamp,
                "level": record.levelname,
                "trace_id": trace_id,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                log_obj["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_obj)

        msg = record.getMessage()
        exc_text = f"\n{self.formatException(record.exc_info)}" if record.exc_info else ""
        return f"[{timestamp}] [{record.levelname:<7}] [{trace_id}] {record.name}: {msg}{exc_text}"


def setup_structured_logging(level: int = logging.INFO, json_format: bool = False) -> None:
    """Configure root logger with structured trace-aware logging."""
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(StructuredLogFormatter(json_output=json_format))
    root.addHandler(handler)
