"""
Simple in-process metrics counters.
This is intentionally lightweight to avoid extra dependencies on Render free-tier.
Use Redis/Prometheus for production-grade metrics.
"""
import threading
from typing import Dict


_lock = threading.Lock()
_counters: Dict[str, int] = {}


def inc(counter_name: str, amount: int = 1) -> None:
    """Increment a named counter by `amount` (default 1)."""
    with _lock:
        _counters[counter_name] = _counters.get(counter_name, 0) + amount


def get_metrics() -> Dict[str, int]:
    """Return a snapshot of current counters."""
    with _lock:
        return dict(_counters)


def reset_metrics() -> None:
    """Reset all counters (useful for tests)."""
    with _lock:
        _counters.clear()
