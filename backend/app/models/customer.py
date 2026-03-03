"""
Customer model for storing customer information.
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.db.base import Base


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


class Customer(Base):
    """Customer model."""
    
    __tablename__ = "customers"
    
    # Primary Key
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    
    # Customer Information
    phone_number = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    
    # Address Information
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    
    # Customer Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)
    
    # Statistics
    total_calls = Column(Integer, default=0, nullable=False)
    total_appointments = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    last_call_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    calls = relationship("Call", back_populates="customer", cascade="all, delete-orphan", lazy="select", repr=False)
    appointments = relationship("Appointment", back_populates="customer", cascade="all, delete-orphan", lazy="select", repr=False)
    conversation_states = relationship("ConversationStateModel", back_populates="customer", lazy="select", repr=False)
    
    def __repr__(self):
        return f"<Customer(id={self.id}, phone={self.phone_number}, name={self.name})>"

