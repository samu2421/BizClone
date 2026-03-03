"""create_conversation_states_table

Revision ID: 18e7100e6823
Revises: 124ea28e0e49
Create Date: 2026-02-27 02:33:44.310300

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '18e7100e6823'
down_revision: Union[str, None] = '124ea28e0e49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create conversation_states table."""
    # Create conversation_status enum if not exists
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE conversationstatus AS ENUM ("
        "'active', 'awaiting_response', 'completed', 'abandoned', 'escalated'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    # Create conversation_state enum if not exists
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE conversationstate AS ENUM ("
        "'initial', 'greeting', 'intent_identified', 'collecting_info', "
        "'awaiting_date', 'awaiting_location', 'awaiting_service_details', "
        "'awaiting_confirmation', 'confirmed', 'providing_info', "
        "'scheduling', 'rescheduling', 'canceling', "
        "'emergency_handling', 'escalation_needed', 'completed', 'failed'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    # Create conversation_states table
    op.create_table(
        'conversation_states',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('call_id', sa.String(), nullable=False),
        sa.Column('customer_id', sa.String(), nullable=False),
        sa.Column('appointment_id', sa.String(), nullable=True),
        sa.Column('status', postgresql.ENUM(
            'active', 'awaiting_response', 'completed', 'abandoned', 'escalated',
            name='conversationstatus',
            create_type=False
        ), nullable=False),
        sa.Column('current_state', postgresql.ENUM(
            'initial', 'greeting', 'intent_identified', 'collecting_info',
            'awaiting_date', 'awaiting_location', 'awaiting_service_details',
            'awaiting_confirmation', 'confirmed', 'providing_info',
            'scheduling', 'rescheduling', 'canceling',
            'emergency_handling', 'escalation_needed', 'completed', 'failed',
            name='conversationstate',
            create_type=False
        ), nullable=False),
        sa.Column('previous_state', postgresql.ENUM(
            'initial', 'greeting', 'intent_identified', 'collecting_info',
            'awaiting_date', 'awaiting_location', 'awaiting_service_details',
            'awaiting_confirmation', 'confirmed', 'providing_info',
            'scheduling', 'rescheduling', 'canceling',
            'emergency_handling', 'escalation_needed', 'completed', 'failed',
            name='conversationstate',
            create_type=False
        ), nullable=True),
        sa.Column('context', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('turn_count', sa.Integer(), nullable=False),
        sa.Column('last_message', sa.Text(), nullable=True),
        sa.Column('last_response', sa.Text(), nullable=True),
        sa.Column('needs_human', sa.Boolean(), nullable=False),
        sa.Column('is_emergency', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_interaction_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ),
    )

    # Create indexes
    op.create_index(op.f('ix_conversation_states_id'), 'conversation_states', ['id'])
    op.create_index(op.f('ix_conversation_states_call_id'), 'conversation_states', ['call_id'], unique=True)
    op.create_index(op.f('ix_conversation_states_customer_id'), 'conversation_states', ['customer_id'])
    op.create_index(op.f('ix_conversation_states_appointment_id'), 'conversation_states', ['appointment_id'])
    op.create_index(op.f('ix_conversation_states_status'), 'conversation_states', ['status'])
    op.create_index(op.f('ix_conversation_states_current_state'), 'conversation_states', ['current_state'])
    op.create_index(op.f('ix_conversation_states_created_at'), 'conversation_states', ['created_at'])
    op.create_index(op.f('ix_conversation_states_last_interaction_at'), 'conversation_states', ['last_interaction_at'])


def downgrade() -> None:
    """Drop conversation_states table."""
    # Drop indexes
    op.drop_index(op.f('ix_conversation_states_last_interaction_at'), 'conversation_states')
    op.drop_index(op.f('ix_conversation_states_created_at'), 'conversation_states')
    op.drop_index(op.f('ix_conversation_states_current_state'), 'conversation_states')
    op.drop_index(op.f('ix_conversation_states_status'), 'conversation_states')
    op.drop_index(op.f('ix_conversation_states_appointment_id'), 'conversation_states')
    op.drop_index(op.f('ix_conversation_states_customer_id'), 'conversation_states')
    op.drop_index(op.f('ix_conversation_states_call_id'), 'conversation_states')
    op.drop_index(op.f('ix_conversation_states_id'), 'conversation_states')

    # Drop table
    op.drop_table('conversation_states')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS conversationstate")
    op.execute("DROP TYPE IF EXISTS conversationstatus")
