"""
Record model for audit and history tracking of all system records.

Stores past, present, and future system records such as calls, transcripts,
events, tasks, appointments, and other relevant system actions.
Records are never automatically deleted - for audit compliance.
"""
from sqlalchemy import Column, String, DateTime, Text, JSON, Index
from datetime import datetime, timezone
import uuid

from app.db.base import Base


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


class Record(Base):
    """
    Audit table for all system records.

    Use record_type to categorize: call, transcript, event, task,
    appointment, escalation, etc. Use entity_id and entity_type for
    referencing the source entity.
    """

    __tablename__ = "records"

    # Primary Key
    id = Column(String, primary_key=True, default=generate_uuid, index=True)

    # Record classification
    record_type = Column(String, nullable=False, index=True)
    # Types: call, transcript, event, task, appointment, escalation,
    # intent_classification, entity_extraction, priority_detection,
    # scheduling, system_action, etc.

    # Source entity reference (optional)
    entity_id = Column(String, nullable=True, index=True)
    entity_type = Column(String, nullable=True, index=True)
    # entity_type: call, transcript, call_event, appointment, etc.

    # Payload - flexible JSON for record-specific data
    payload = Column(JSON, nullable=True)

    # Human-readable summary (optional)
    summary = Column(Text, nullable=True)

    # Timestamps - records are never auto-deleted
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Composite index for common queries
    __table_args__ = (
        Index("ix_records_type_created", "record_type", "created_at"),
        Index(
            "ix_records_entity_created",
            "entity_type", "entity_id", "created_at",
        ),
    )

    def __repr__(self):
        return (
            f"<Record(id={self.id}, record_type={self.record_type}, "
            f"entity_type={self.entity_type}, entity_id={self.entity_id})>"
        )
