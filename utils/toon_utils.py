"""TOON conversion utilities powered by the official toon-format implementation.

toon-format is the official Python implementation of the TOON specification
(toon-format/spec), passes every official conformance fixture, and guarantees
lossless round-trips for every JSON-compatible value. Decoding auto-detects
the delimiter from tabular headers per the specification, so no delimiter
hint is needed when parsing.
"""

from typing import Any

import toon_format

# Delimiter names accepted by the tools, mapped to the literal characters
# expected by toon-format.
DELIMITER_CHARS = {
    'comma': ',',
    'tab': '\t',
    'pipe': '|',
}

_DELIMITER_ALIASES = {
    'comma': 'comma',
    ',': 'comma',
    'tab': 'tab',
    '\\t': 'tab',
    '\t': 'tab',
    'pipe': 'pipe',
    '|': 'pipe',
}


def normalize_delimiter(value: Any) -> str:
    """Normalize a user supplied delimiter value to 'comma', 'tab' or 'pipe'.

    Accepts the canonical names ('comma', 'tab', 'pipe') and common aliases
    (',', '\\t', '|'). Defaults to 'comma' when value is empty.
    """
    if value is None:
        return 'comma'
    raw = str(value).lower()
    stripped = raw.strip()
    if not stripped:
        # A lone whitespace character (e.g. a real tab) is a meaningful
        # delimiter; a truly empty value falls back to the default.
        return _DELIMITER_ALIASES.get(raw, 'comma')
    if stripped not in _DELIMITER_ALIASES:
        raise ValueError(f"Invalid delimiter: {value!r}, must be one of {tuple(DELIMITER_CHARS)}")
    return _DELIMITER_ALIASES[stripped]


def encode_toon(data: Any, delimiter: str = 'comma') -> str:
    """Encode a Python object to a TOON string in the official spec format."""
    return toon_format.dumps(data, delimiter=DELIMITER_CHARS[normalize_delimiter(delimiter)])


def decode_toon(toon_str: str) -> Any:
    """Decode a TOON string to a Python object.

    The delimiter is auto-detected from tabular headers, as the specification
    requires. Raises toon_format.ToonDecodeError on invalid input.
    """
    return toon_format.loads(toon_str)


def compute_stats(original: str, toon_str: str) -> dict[str, Any]:
    """Compute compression statistics between the original JSON and TOON text.

    compression_ratio is the saved fraction, e.g. 1000 -> 400 chars gives 0.6
    (60% smaller).
    """
    original_chars = len(original)
    toon_chars = len(toon_str)
    ratio = round(1 - toon_chars / original_chars, 4) if original_chars else 0.0
    return {
        'original_chars': original_chars,
        'toon_chars': toon_chars,
        'compression_ratio': ratio,
        'savings_percent': round(ratio * 100, 2),
    }
