"""Backfill per-user trial end dates

Revision ID: 20251210_update_trial_end_dates
Revises: 20251208_add_submission_device_metadata
Create Date: 2025-12-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20251210_update_trial_end_dates'
down_revision: Union[str, Sequence[str], None] = '20251208_add_submission_device_metadata'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # For any trialing user lacking a trial end or having an obviously stale timestamp,
    # set it to 3 days after their subscription start (fallback to created_at or now()).
    op.execute(
        """
        UPDATE users
        SET trial_ends_at = COALESCE(subscription_start_date, created_at, NOW()) + INTERVAL '3 days'
        WHERE subscription_status = 'trialing'
          AND (trial_ends_at IS NULL OR trial_ends_at < COALESCE(subscription_start_date, created_at, NOW()));
        """
    )


def downgrade() -> None:
    # No-op downgrade (cannot reliably restore previous timestamps)
    pass
