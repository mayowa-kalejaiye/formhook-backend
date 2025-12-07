"""Add is_admin flag to users

Revision ID: add_is_admin_flag
Revises: add_trial_metadata
Create Date: 2025-12-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_is_admin_flag'
down_revision: Union[str, Sequence[str], None] = 'add_trial_metadata'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.create_index('ix_users_is_admin', 'users', ['is_admin'])
    op.alter_column('users', 'is_admin', server_default=None)


def downgrade() -> None:
    op.drop_index('ix_users_is_admin', table_name='users')
    op.drop_column('users', 'is_admin')
*** End of File***
