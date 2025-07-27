"""create webhook_delivery table

Revision ID: 3a3d99b1a060
Revises: ebc97af20988
Create Date: 2025-07-27 18:03:00.296851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3a3d99b1a060'
down_revision: Union[str, Sequence[str], None] = 'ebc97af20988'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'webhook_delivery',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('form_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('forms.id')),
        sa.Column('submission_id', sa.Integer, nullable=True),
        sa.Column('status_code', sa.Integer, nullable=True),
        sa.Column('success', sa.Boolean, nullable=False, default=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('headers_sent', postgresql.JSONB, nullable=True),
        sa.Column('response_body', sa.Text, nullable=True),
        sa.Column('retry_count', sa.Integer, nullable=False, default=0),
        sa.Column('duration_ms', sa.Integer, nullable=True),
    )
    op.create_index('ix_webhook_delivery_form_id', 'webhook_delivery', ['form_id'])
def downgrade():
    op.drop_index('ix_webhook_delivery_form_id', table_name='webhook_delivery')
    op.drop_table('webhook_delivery')
