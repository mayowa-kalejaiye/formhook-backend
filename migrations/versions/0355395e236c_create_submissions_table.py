"""create submissions table

Revision ID: 0355395e236c
Revises: 3a3d99b1a060
Create Date: 2025-07-27 18:03:32.085940

"""
from typing import Sequence, Union


from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0355395e236c'
down_revision: Union[str, Sequence[str], None] = '3a3d99b1a060'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'submissions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('form_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('forms.id'), nullable=False),
        sa.Column('data', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('submissions')
