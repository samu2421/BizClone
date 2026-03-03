"""create_appointments_table

Revision ID: 124ea28e0e49
Revises: c22db06eec89
Create Date: 2026-02-27 02:23:48.986401

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '124ea28e0e49'
down_revision: Union[str, None] = 'c22db06eec89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create appointment_status enum if not exists
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE appointmentstatus AS ENUM ("
        "'pending', 'confirmed', 'scheduled', 'completed', 'canceled', 'no_show'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    # Create urgency_level enum if not exists
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE urgencylevel AS ENUM ("
        "'low', 'medium', 'high', 'urgent', 'emergency'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    # Create appointments table
    op.create_table(
        'appointments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('call_id', sa.String(), nullable=False),
        sa.Column('customer_id', sa.String(), nullable=False),
        sa.Column('status', postgresql.ENUM(
            'pending', 'confirmed', 'scheduled', 'completed',
            'canceled', 'no_show',
            name='appointmentstatus',
            create_type=False
        ), nullable=False),
        sa.Column('requested_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'requested_time_start',
            sa.DateTime(timezone=True),
            nullable=True
        ),
        sa.Column(
            'requested_time_end',
            sa.DateTime(timezone=True),
            nullable=True
        ),
        sa.Column('date_time_text', sa.Text(), nullable=True),
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'scheduled_time_start',
            sa.DateTime(timezone=True),
            nullable=True
        ),
        sa.Column(
            'scheduled_time_end',
            sa.DateTime(timezone=True),
            nullable=True
        ),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=True),
        sa.Column('zip_code', sa.String(), nullable=True),
        sa.Column('location_text', sa.Text(), nullable=True),
        sa.Column('service_type', sa.String(), nullable=True),
        sa.Column('service_description', sa.Text(), nullable=True),
        sa.Column('urgency', postgresql.ENUM(
            'low', 'medium', 'high', 'urgent', 'emergency',
            name='urgencylevel',
            create_type=False
        ), nullable=False),
        sa.Column('urgency_reason', sa.Text(), nullable=True),
        sa.Column('contact_phone', sa.String(), nullable=True),
        sa.Column('contact_email', sa.String(), nullable=True),
        sa.Column('contact_name', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
    )

    # Create indexes
    op.create_index(op.f('ix_appointments_id'), 'appointments', ['id'])
    op.create_index(
        op.f('ix_appointments_call_id'),
        'appointments',
        ['call_id']
    )
    op.create_index(
        op.f('ix_appointments_customer_id'),
        'appointments',
        ['customer_id']
    )
    op.create_index(
        op.f('ix_appointments_scheduled_date'),
        'appointments',
        ['scheduled_date']
    )
    op.create_index(
        op.f('ix_appointments_created_at'),
        'appointments',
        ['created_at']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_appointments_created_at'), 'appointments')
    op.drop_index(op.f('ix_appointments_scheduled_date'), 'appointments')
    op.drop_index(op.f('ix_appointments_customer_id'), 'appointments')
    op.drop_index(op.f('ix_appointments_call_id'), 'appointments')
    op.drop_index(op.f('ix_appointments_id'), 'appointments')

    # Drop table
    op.drop_table('appointments')

    # Drop enums
    op.execute('DROP TYPE urgencylevel')
    op.execute('DROP TYPE appointmentstatus')
