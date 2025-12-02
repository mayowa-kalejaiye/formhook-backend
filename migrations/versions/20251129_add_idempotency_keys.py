"""add idempotency keys table

Revision ID: 20251129_add_idempotency_keys
Revises: 5fadffbd2fe8
Create Date: 2025-11-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20251129_add_idempotency_keys'
down_revision: Union[str, Sequence[str], None] = '5fadffbd2fe8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create idempotency_keys table."""
    op.create_table(
        'idempotency_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('form_id', sa.String(), nullable=False),
        sa.Column('submission_id', sa.Integer(), sa.ForeignKey('submissions.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash', 'form_id', name='uq_idempotency_key_form')
    )

    # Indexes
    op.create_index('ix_idempotency_keys_id', 'idempotency_keys', ['id'], unique=False)
    op.create_index('ix_idempotency_keys_key_hash', 'idempotency_keys', ['key_hash'], unique=False)
    op.create_index('ix_idempotency_keys_form_id', 'idempotency_keys', ['form_id'], unique=False)


def downgrade() -> None:
    """Drop idempotency_keys table."""
    op.drop_index('ix_idempotency_keys_form_id', table_name='idempotency_keys')
    op.drop_index('ix_idempotency_keys_key_hash', table_name='idempotency_keys')
    op.drop_index('ix_idempotency_keys_id', table_name='idempotency_keys')
    op.drop_table('idempotency_keys')
