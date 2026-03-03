"""add_intent_confidence_to_calls

Revision ID: c22db06eec89
Revises: e5f614afcd64
Create Date: 2026-02-27 02:13:06.892112

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c22db06eec89'
down_revision: Union[str, None] = 'e5f614afcd64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add intent_confidence column to calls table
    op.add_column('calls', sa.Column('intent_confidence', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove intent_confidence column from calls table
    op.drop_column('calls', 'intent_confidence')
