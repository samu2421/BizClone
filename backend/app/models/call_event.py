"""
CallEvent model for storing call lifecycle events.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.db.base import Base


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


class CallEvent(Base):
    """CallEvent model for tracking call lifecycle events."""
    
    __tablename__ = "call_events"
    
    # Primary Key
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    
    # Call Reference
    call_id = Column(String, ForeignKey("calls.id"), nullable=False, index=True)
    
    # Event Information
    event_type = Column(String, nullable=False, index=True)
    # Event types: "call_initiated", "call_ringing", "call_answered", "call_completed",
    # "recording_started", "recording_completed", "transcription_started", 
    # "transcription_completed", "ai_processing_started", "ai_processing_completed",
    # "emergency_detected", "appointment_scheduled", etc.
    
    event_data = Column(JSON, nullable=True)  # Additional event-specific data
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    
    # Relationships
    call = relationship("Call", back_populates="events", lazy="select")
    
    def __repr__(self):
        return f"<CallEvent(id={self.id}, call_id={self.call_id}, event_type={self.event_type})>"

