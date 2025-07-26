"""
Add advanced fields to WebhookDeliveryLog
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('webhook_delivery', sa.Column('form_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('webhook_delivery', sa.Column('success', sa.Boolean(), nullable=True))
    op.add_column('webhook_delivery', sa.Column('headers_sent', postgresql.JSONB, nullable=True))
    op.add_column('webhook_delivery', sa.Column('response_body', sa.Text(), nullable=True))
    op.add_column('webhook_delivery', sa.Column('retry_count', sa.Integer(), nullable=True))
    op.add_column('webhook_delivery', sa.Column('duration_ms', sa.Integer(), nullable=True))
    op.create_index('ix_webhook_delivery_form_id', 'webhook_delivery', ['form_id'])

def downgrade():
    op.drop_index('ix_webhook_delivery_form_id', table_name='webhook_delivery')
    op.drop_column('webhook_delivery', 'form_id')
    op.drop_column('webhook_delivery', 'success')
    op.drop_column('webhook_delivery', 'headers_sent')
    op.drop_column('webhook_delivery', 'response_body')
    op.drop_column('webhook_delivery', 'retry_count')
    op.drop_column('webhook_delivery', 'duration_ms')
