"""add token version to users

Revision ID: 20260422_add_token_version_to_users
Revises: 20260422_add_password_resets
Create Date: 2026-04-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260422_add_token_version_to_users'
down_revision: Union[str, Sequence[str], None] = '20260422_add_password_resets'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'token_version')