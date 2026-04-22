"""add auth security counters

Revision ID: 20260422_add_auth_security_counters
Revises: 20260422_add_token_version_to_users
Create Date: 2026-04-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260422_add_auth_security_counters'
down_revision: Union[str, Sequence[str], None] = '20260422_add_token_version_to_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auth_security_counters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('ip_address', sa.String(length=64), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('endpoint', 'email', 'ip_address', name='uq_auth_security_counter_key')
    )
    op.create_index(op.f('ix_auth_security_counters_id'), 'auth_security_counters', ['id'], unique=False)
    op.create_index(op.f('ix_auth_security_counters_endpoint'), 'auth_security_counters', ['endpoint'], unique=False)
    op.create_index(op.f('ix_auth_security_counters_email'), 'auth_security_counters', ['email'], unique=False)
    op.create_index(op.f('ix_auth_security_counters_ip_address'), 'auth_security_counters', ['ip_address'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_auth_security_counters_ip_address'), table_name='auth_security_counters')
    op.drop_index(op.f('ix_auth_security_counters_email'), table_name='auth_security_counters')
    op.drop_index(op.f('ix_auth_security_counters_endpoint'), table_name='auth_security_counters')
    op.drop_index(op.f('ix_auth_security_counters_id'), table_name='auth_security_counters')
    op.drop_table('auth_security_counters')
