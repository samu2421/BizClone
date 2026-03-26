"""create_records_table

Revision ID: a1b2c3d4e5f6
Revises: 18e7100e6823
Create Date: 2026-03-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '18e7100e6823'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create records table for audit/history tracking."""
    op.create_table(
        'records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('record_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=True),
        sa.Column('entity_type', sa.String(), nullable=True),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes
    op.create_index(op.f('ix_records_id'), 'records', ['id'])
    op.create_index(op.f('ix_records_record_type'), 'records', ['record_type'])
    op.create_index(op.f('ix_records_entity_id'), 'records', ['entity_id'])
    op.create_index(op.f('ix_records_entity_type'), 'records', ['entity_type'])
    op.create_index(op.f('ix_records_created_at'), 'records', ['created_at'])
    op.create_index(op.f('ix_records_updated_at'), 'records', ['updated_at'])
    op.create_index('ix_records_type_created', 'records', ['record_type', 'created_at'])
    op.create_index('ix_records_entity_created', 'records', ['entity_type', 'entity_id', 'created_at'])


def downgrade() -> None:
    """Drop records table."""
    op.drop_index('ix_records_entity_created', 'records')
    op.drop_index('ix_records_type_created', 'records')
    op.drop_index(op.f('ix_records_updated_at'), 'records')
    op.drop_index(op.f('ix_records_created_at'), 'records')
    op.drop_index(op.f('ix_records_entity_type'), 'records')
    op.drop_index(op.f('ix_records_entity_id'), 'records')
    op.drop_index(op.f('ix_records_record_type'), 'records')
    op.drop_index(op.f('ix_records_id'), 'records')
    op.drop_table('records')
