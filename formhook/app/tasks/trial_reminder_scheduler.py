"""Async loop for recurring trial reminder emails."""
from __future__ import annotations

import asyncio
import logging

from ..core.config import settings
from ..core.database import SessionLocal
from ..services.trial_reminder import send_trial_reminders

logger = logging.getLogger(__name__)


async def run_trial_reminder_loop(stop_event: asyncio.Event) -> None:
    """Run reminder job until stop event is set."""
    interval_minutes = max(settings.TRIAL_REMINDER_INTERVAL_MINUTES, 15)
    logger.info(
        "Trial reminder loop started (interval=%s minutes)",
        interval_minutes,
    )
    try:
        while not stop_event.is_set():
            await asyncio.to_thread(_send_once)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_minutes * 60)
            except asyncio.TimeoutError:
                continue
    finally:
        logger.info("Trial reminder loop stopped")


def _send_once() -> None:
    db = SessionLocal()
    try:
        stats = send_trial_reminders(db)
        if stats["day2"] or stats["day3"]:
            logger.info(
                "Trial reminders sent (day2=%s, day3=%s)",
                stats["day2"],
                stats["day3"],
            )
    except Exception:
        logger.exception("Trial reminder execution failed")
    finally:
        db.close()
