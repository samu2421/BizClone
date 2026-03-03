"""
Transcript model for storing call transcriptions.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.db.base import Base


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


class Transcript(Base):
    """Transcript model."""
    
    __tablename__ = "transcripts"
    
    # Primary Key
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    
    # Call Reference
    call_id = Column(String, ForeignKey("calls.id"), nullable=False, index=True)
    
    # Transcript Content
    text = Column(Text, nullable=False)
    language = Column(String, default="en", nullable=False)
    
    # Whisper Metadata
    confidence = Column(Float, nullable=True)  # Average confidence score
    model_used = Column(String, nullable=True)  # e.g., "whisper-base"
    processing_time_seconds = Column(Float, nullable=True)
    
    # Audio Information
    audio_duration_seconds = Column(Float, nullable=True)
    audio_file_path = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    
    # Relationships
    call = relationship("Call", back_populates="transcripts", lazy="select", repr=False)
    
    def __repr__(self):
        return f"<Transcript(id={self.id}, call_id={self.call_id}, text_preview={self.text[:50]}...)>"

