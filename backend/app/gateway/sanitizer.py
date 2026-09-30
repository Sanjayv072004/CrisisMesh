"""Sanitizer: Unicode Normalization, Zero-Width Stripping, and Spotlighting Delimiters."""
from __future__ import annotations
import html
import re
import unicodedata
from typing import Tuple

# Zero-width, byte-order mark, and direction override characters
ZERO_WIDTH_CHARS = {
    '\u200b',  # zero-width space
    '\u200c',  # zero-width non-joiner
    '\u200d',  # zero-width joiner
    '\u200e',  # left-to-right mark
    '\u200f',  # right-to-left mark
    '\ufeff',  # byte order mark / zero-width no-break space
    '\u202a',  # left-to-right embedding
    '\u202b',  # right-to-left embedding
    '\u202c',  # pop directional formatting
    '\u202d',  # left-to-right override
    '\u202e',  # right-to-left override
}

SPOTLIGHT_START = "<<<UNTRUSTED_CIVILIAN_REPORT>>>"
SPOTLIGHT_END = "<<<END_UNTRUSTED_CIVILIAN_REPORT>>>"


def sanitize_text(text: str, max_length: int = 2000) -> Tuple[str, str, int]:
    """Sanitize raw incoming text and apply spotlighting delimiters.
    
    Returns:
        (sanitized_clean_text, spotlit_delimited_text, stripped_zero_width_count)
    """
    if not text:
        return "", f"{SPOTLIGHT_START}\n\n{SPOTLIGHT_END}", 0

    # 1. Unicode Normalization (NFKC)
    normalized = unicodedata.normalize("NFKC", text)

    # 2. Detect & strip zero-width characters
    stripped_count = sum(1 for ch in normalized if ch in ZERO_WIDTH_CHARS)
    clean_chars = [ch for ch in normalized if ch not in ZERO_WIDTH_CHARS]
    cleaned = "".join(clean_chars)

    # 3. Strip non-printable control characters except \n, \r, \t
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)

    # 4. Escape / Neutralize HTML markup
    neutralized = html.escape(cleaned)

    # 5. Enforce length limit
    if len(neutralized) > max_length:
        neutralized = neutralized[:max_length]

    # 6. Apply spotlighting delimiters to isolate untrusted text before LLM consumption
    spotlit = f"{SPOTLIGHT_START}\n{neutralized}\n{SPOTLIGHT_END}"

    return neutralized, spotlit, stripped_count
