"""Time-granularity truncation.

A time dimension can be rolled up to a grain (day, week, month, quarter,
year). Rather than depend on a specific warehouse, we emit the truncation
inline. SQLite gets strftime-based expressions (its date functions are a bit
idiosyncratic); every other dialect gets a standard DATE_TRUNC.

Weeks start on Monday, following the ISO convention.
"""

from __future__ import annotations

GRAINS = ("day", "week", "month", "quarter", "year")


def truncate(expr: str, grain: str, dialect: str = "sqlite") -> str:
    """Return a SQL expression that truncates ``expr`` down to ``grain``."""
    if grain not in GRAINS:
        raise ValueError(
            f"unknown grain '{grain}', expected one of {', '.join(GRAINS)}"
        )
    if dialect == "sqlite":
        return _sqlite(expr, grain)
    return f"DATE_TRUNC('{grain}', {expr})"


def _sqlite(expr: str, grain: str) -> str:
    if grain == "day":
        return f"date({expr})"
    if grain == "year":
        return f"strftime('%Y-01-01', {expr})"
    if grain == "month":
        return f"strftime('%Y-%m-01', {expr})"
    if grain == "quarter":
        # First month of the quarter: 1, 4, 7 or 10, zero padded.
        month = f"(((CAST(strftime('%m', {expr}) AS INTEGER) - 1) / 3) * 3 + 1)"
        padded = f"substr('0' || {month}, -2)"
        return f"strftime('%Y', {expr}) || '-' || {padded} || '-01'"
    # week: step back to the most recent Monday.
    offset = f"((CAST(strftime('%w', {expr}) AS INTEGER) + 6) % 7)"
    return f"date({expr}, '-' || {offset} || ' days')"
