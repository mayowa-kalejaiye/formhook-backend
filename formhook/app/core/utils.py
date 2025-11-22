"""Common utilities for the FormHook app.

Provides a single helper for obtaining a timezone-aware UTC "now".
"""
from datetime import datetime, timezone


def now_utc() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)
