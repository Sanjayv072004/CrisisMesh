"""Log Redaction Filter: Automatic Masking of API Keys, Tokens, Nonces and PII."""
from __future__ import annotations
import logging
import re
from typing import List, Tuple

REDACTION_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Google / Gemini API Keys
    (re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "[REDACTED_GEMINI_KEY]"),
    # OpenAI API Keys
    (re.compile(r"sk-[a-zA-Z0-9]{20,T3BlbkFJ[a-zA-Z0-9]+|sk-[a-zA-Z0-9]{32,}"), "[REDACTED_OPENAI_KEY]"),
    # Bearer authorization tokens
    (re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{15,}"), "Bearer [REDACTED_TOKEN]"),
    # Generic high-entropy hex secrets (e.g. HMAC secrets, private keys >= 32 chars)
    (re.compile(r"(?i)(secret|password|private_key|token)[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9_\-]{16,})[\"']?"), r"\1=[REDACTED_SECRET]"),
    # Indian Mobile Numbers (+91 or 10 digits starting with 6-9)
    (re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b"), "[REDACTED_PHONE]"),
    # Aadhaar numbers (12 digits with optional spaces/hyphens)
    (re.compile(r"\b\d{4}[\s\-]\d{4}[\s\-]\d{4}\b"), "[REDACTED_AADHAAR]"),
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[REDACTED_EMAIL]"),
]


def redact_sensitive_text(text: str) -> str:
    """Scrub sensitive keys, credentials, and personally identifiable information from strings."""
    if not isinstance(text, str):
        text = str(text)
    sanitized = text
    for pattern, replacement in REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class RedactionFilter(logging.Filter):
    """Logging filter that redacts all log records before outputting."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: redact_sensitive_text(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(redact_sensitive_text(str(v)) for v in record.args)
        return True


def apply_redaction_to_logger(logger: logging.Logger) -> None:
    """Attach the RedactionFilter to the specified logger and all its handlers."""
    redaction_filter = RedactionFilter()
    logger.addFilter(redaction_filter)
    for handler in logger.handlers:
        handler.addFilter(redaction_filter)
