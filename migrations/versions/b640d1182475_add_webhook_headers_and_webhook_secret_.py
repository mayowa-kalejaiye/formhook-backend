"""add webhook_headers and webhook_secret to forms

Revision ID: b640d1182475
Revises: ca5212d09bc8
Create Date: 2025-07-27 17:54:56.656730

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



# revision identifiers, used by Alembic.
revision: str = 'b640d1182475'
down_revision: Union[str, Sequence[str], None] = 'ca5212d09bc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('forms', sa.Column('webhook_headers', postgresql.JSONB, nullable=True))
    op.add_column('forms', sa.Column('webhook_secret', sa.String(), nullable=True))

def downgrade():
    op.drop_column('forms', 'webhook_headers')
    op.drop_column('forms', 'webhook_secret')
