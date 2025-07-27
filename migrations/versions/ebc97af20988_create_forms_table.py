"""create forms table

Revision ID: ebc97af20988
Revises: b640d1182475
Create Date: 2025-07-27 18:02:11.688967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ebc97af20988'
down_revision: Union[str, Sequence[str], None] = 'b640d1182475'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'forms',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('webhook_url', sa.String(), nullable=True),
        sa.Column('webhook_headers', postgresql.JSONB, nullable=True),
        sa.Column('webhook_secret', sa.String(), nullable=True),
        sa.Column('notification_email', sa.String(), nullable=True),
        sa.Column('redirect_url', sa.String(), nullable=True),
        sa.Column('success_message', sa.String(), nullable=True),
        sa.Column('fields', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
def downgrade():
    op.drop_table('forms')
