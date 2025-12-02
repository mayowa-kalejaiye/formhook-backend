"""Add trial metadata and migrate users to starter tier

Revision ID: add_trial_metadata
Revises: add_subscription_tracking
Create Date: 2025-12-02 00:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime, timedelta, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = 'add_trial_metadata'
down_revision: Union[str, Sequence[str], None] = 'add_subscription_tracking'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True))

    bind = op.get_bind()
    users_table = table(
        'users',
        column('subscription_tier', sa.String()),
        column('subscription_status', sa.String()),
        column('trial_ends_at', sa.DateTime(timezone=True)),
    )

    trial_end = datetime.now(timezone.utc) + timedelta(days=3)

    bind.execute(
        users_table.update()
        .where(users_table.c.subscription_tier == 'free')
        .values(
            subscription_tier='starter',
            subscription_status='trialing',
            trial_ends_at=trial_end,
        )
    )


def downgrade() -> None:
    op.drop_column('users', 'trial_ends_at')
*** End of File***
