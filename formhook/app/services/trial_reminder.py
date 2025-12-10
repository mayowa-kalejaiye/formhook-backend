"""Utilities for emailing trial users as their 3-day window winds down."""
from __future__ import annotations

import logging
from datetime import timedelta
import time
from typing import Dict

from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.utils import now_utc
from ..models.user import User
from .email import send_email

logger = logging.getLogger(__name__)


class TrialReminderService:
    """Sends day 2 and day 3 trial reminders via Resend."""

    TRIAL_LENGTH_DAYS = 3
    DAY2_KEY = "trial_day2_email_sent_at"
    DAY3_KEY = "trial_day3_email_sent_at"

    def __init__(self, db: Session):
        self.db = db
        self._min_interval = max(settings.RESEND_MIN_INTERVAL_SECONDS, 0.0)
        self._last_send_ts = 0.0

    def send_due_reminders(self) -> Dict[str, int]:
        """Send reminder emails for all users whose trial reminders are due."""
        now = now_utc()
        stats = {"day2": 0, "day3": 0}

        trial_users = (
            self.db.query(User)
            .filter(User.subscription_status == "trialing")
            .filter(User.trial_ends_at.isnot(None))
            .all()
        )

        dirty = False

        for user in trial_users:
            trial_end = user.trial_ends_at
            if not trial_end:
                continue

            trial_start = trial_end - timedelta(days=self.TRIAL_LENGTH_DAYS)
            metadata_source = user.subscription_metadata or {}
            if not isinstance(metadata_source, dict):
                metadata_source = {}
            metadata = dict(metadata_source)
            updated = False

            if self._should_send(now, trial_start + timedelta(days=1), trial_end, metadata, self.DAY2_KEY):
                if self._deliver_email(user, trial_end, now, day=2):
                    metadata[self.DAY2_KEY] = now.isoformat()
                    stats["day2"] += 1
                    updated = True

            if self._should_send(now, trial_start + timedelta(days=2), trial_end, metadata, self.DAY3_KEY):
                if self._deliver_email(user, trial_end, now, day=3):
                    metadata[self.DAY3_KEY] = now.isoformat()
                    stats["day3"] += 1
                    updated = True

            if updated:
                user.subscription_metadata = metadata
                dirty = True

        if dirty:
            self.db.commit()
        else:
            self.db.expire_all()

        return stats

    def _should_send(
        self,
        now,
        trigger_at,
        trial_end,
        metadata: Dict[str, str],
        metadata_key: str
    ) -> bool:
        if metadata.get(metadata_key):
            return False
        if now < trigger_at:
            return False
        return now < trial_end + timedelta(days=1)

    def _deliver_email(self, user: User, trial_end, now, day: int) -> bool:
        subject, html = self._build_email_copy(user, trial_end, now, day)
        try:
            self._respect_rate_limit()
            response = send_email(
                to_email=user.email,
                subject=subject,
                html_content=html
            )
            return True
        except Exception:
            logger.exception("Failed to send trial day %s reminder to %s", day, user.email)
            return False

    def _respect_rate_limit(self) -> None:
        if self._min_interval <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_send_ts if self._last_send_ts else None
        if elapsed is not None and elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_send_ts = time.monotonic()

    def _build_email_copy(self, user: User, trial_end, now, day: int) -> tuple[str, str]:
        billing_url = f"{settings.FRONTEND_URL.rstrip('/')}/billing"
        trial_end_display = trial_end.strftime("%B %d, %Y")
        hours_left = max(int((trial_end - now).total_seconds() // 3600), 0)
        local_part = user.email.split('@')[0] if '@' in user.email else user.email
        recipient_name = local_part.replace('.', ' ').title()

        if day == 2:
            subject = "You're halfway through your FormHook trial"
            intro = "You're two days into your 3-day Starter trial."
            urgency = "There are still 48 hours to experience automated webhooks, submission analytics, and instant email alerts."
        else:
            subject = "Your FormHook trial ends tomorrow"
            intro = "You're entering the final stretch of your FormHook trial."
            urgency = (
                "Your forms will pause once the trial ends unless you pick a paid plan. "
                f"Your current trial is scheduled to end on {trial_end_display}."
            )

        html = f"""
            <p>Hi {recipient_name},</p>
            <p>{intro}</p>
            <p>{urgency}</p>
            <ul>
                <li>Unlimited active forms with spam-resistant endpoints</li>
                <li>Instant Slack-ready webhooks with retries</li>
                <li>Submission analytics and geolocation insights</li>
            </ul>
            <p>Upgrade now to keep submissions flowing past the trial window.</p>
            <p style=\"margin:24px 0\">
                <a href=\"{billing_url}\" style=\"background:#111;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;\">
                    Choose a plan
                </a>
            </p>
            <p>Need help deciding? Just reply to this email and we'll get you sorted.</p>
            <p>— The FormHook Team<br/>Trial ends in approximately {hours_left} hours.</p>
        """
        return subject, html


def send_trial_reminders(db: Session) -> Dict[str, int]:
    """Functional entry point for scripts/tests."""
    service = TrialReminderService(db)
    return service.send_due_reminders()
