"""Small utility helpers used across the bot and bridge.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone


# Telegram MarkdownV2 reserved characters that must be escaped.
_MDV2_SPECIAL = r"_*[]()~`>#+-=|{}.!\\"


def mdv2_escape(text: str) -> str:
    """Escape a string for safe use inside a Telegram MarkdownV2 message."""
    if text is None:
        return ""
    out = []
    for ch in str(text):
        if ch in _MDV2_SPECIAL:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def format_money(amount: float, currency: str = "USD") -> str:
    """Format a money amount with thousands separators and currency suffix."""
    try:
        amt = float(amount)
    except (TypeError, ValueError):
        return f"-- {currency}"
    sign = "-" if amt < 0 else ""
    return f"{sign}{abs(amt):,.2f} {currency}"


def format_pl(amount: float, currency: str = "USD") -> str:
    """Format a P/L value with explicit +/- sign."""
    try:
        amt = float(amount)
    except (TypeError, ValueError):
        return f"-- {currency}"
    sign = "+" if amt >= 0 else "-"
    return f"{sign}{abs(amt):,.2f} {currency}"


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def generate_ea_token(prefix: str = "ea") -> str:
    """Generate a cryptographically strong EA bearer token."""
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def truncate(text: str, limit: int = 80) -> str:
    """Shorten a string for inline display."""
    if text is None:
        return ""
    s = str(text)
    return s if len(s) <= limit else s[: limit - 1] + "…"
