"""DART industry code helpers for peer matching."""

from __future__ import annotations

INDUSTRY_PREFIX_LENGTH = 3


def industry_key(induty_code: object, length: int = INDUSTRY_PREFIX_LENGTH) -> str:
    """Return the configured middle-class industry key from a DART induty_code."""

    code = str(induty_code or "").strip()
    return code[:length] if len(code) >= length else code
