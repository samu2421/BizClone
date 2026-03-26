"""
Conversation state model for tracking multi-turn dialogues.
"""
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON, Integer, Boolean
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
import uuid

from app.db.base import Base


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


class ConversationStatus(str, enum.Enum):
    """Conversation status enumeration."""
    ACTIVE = "active"
    AWAITING_RESPONSE = "awaiting_response"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ESCALATED = "escalated"


class ConversationState(str, enum.Enum):
    """Conversation state enumeration for tracking dialogue flow."""
    INITIAL = "initial"  # First contact
    GREETING = "greeting"  # Exchanging greetings
    INTENT_IDENTIFIED = "intent_identified"  # Intent classified
    COLLECTING_INFO = "collecting_info"  # Gathering details
    AWAITING_DATE = "awaiting_date"  # Waiting for date/time
    AWAITING_LOCATION = "awaiting_location"  # Waiting for address
    AWAITING_SERVICE_DETAILS = "awaiting_service_details"  # Problem description
    AWAITING_CONFIRMATION = "awaiting_confirmation"  # Waiting for yes/no
    CONFIRMED = "confirmed"  # Customer confirmed
    PROVIDING_INFO = "providing_info"  # Providing information to customer
    SCHEDULING = "scheduling"  # Scheduling appointment
    RESCHEDULING = "rescheduling"  # Rescheduling appointment
    CANCELING = "canceling"  # Canceling appointment
    EMERGENCY_HANDLING = "emergency_handling"  # Handling emergency
    ESCALATION_NEEDED = "escalation_needed"  # Needs human intervention
    COMPLETED = "completed"  # Conversation finished
    FAILED = "failed"  # Conversation failed


class ConversationStateModel(Base):
    """Conversation state model for tracking multi-turn dialogues."""

    __tablename__ = "conversation_states"

    # Primary Key
    id = Column(String, primary_key=True, default=generate_uuid, index=True)

    # References
    call_id = Column(
        String, ForeignKey("calls.id"), nullable=False, index=True, unique=True
    )
    customer_id = Column(
        String, ForeignKey("customers.id"), nullable=False, index=True
    )
    appointment_id = Column(
        String, ForeignKey("appointments.id"), nullable=True, index=True
    )

    # State: use enum values ('active') not names ('ACTIVE') for PostgreSQL
    status = Column(
        SQLEnum(
            ConversationStatus,
            values_callable=lambda obj: [e.value for e in obj],
            name="conversationstatus",
            create_constraint=False,
            create_type=False,
        ),
        default=ConversationStatus.ACTIVE,
        nullable=False,
        index=True
    )
    current_state = Column(
        SQLEnum(
            ConversationState,
            values_callable=lambda obj: [e.value for e in obj],
            name="conversationstate",
            create_constraint=False,
            create_type=False,
        ),
        default=ConversationState.INITIAL,
        nullable=False,
        index=True
    )
    previous_state = Column(
        SQLEnum(
            ConversationState,
            values_callable=lambda obj: [e.value for e in obj],
            name="conversationstate",
            create_constraint=False,
            create_type=False,
        ),
        nullable=True
    )

    # Context Data (JSON)
    context = Column(JSON, nullable=True, default=dict)
    # Context: missing_fields, collected_data, last_question,
    # confirmation_pending, turn_count, last_intent

    # Metadata
    turn_count = Column(Integer, default=0, nullable=False)
    last_message = Column(Text, nullable=True)
    last_response = Column(Text, nullable=True)

    # Flags
    needs_human = Column(Boolean, default=False, nullable=False)
    is_emergency = Column(Boolean, default=False, nullable=False)

    # Timestamps
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
        nullable=False
    )
    last_interaction_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    call = relationship(
        "Call", back_populates="conversation_state", lazy="select"
    )
    customer = relationship(
        "Customer", back_populates="conversation_states", lazy="select"
    )
    appointment = relationship(
        "Appointment", back_populates="conversation_state", lazy="select"
    )

    def __repr__(self):
        return (
            f"<ConversationState(id={self.id}, "
            f"status={self.status}, "
            f"state={self.current_state})>"
        )

    def to_dict(self):
        """Convert to dictionary."""
        status_val = self.status.value if self.status else None
        curr_val = self.current_state.value if self.current_state else None
        prev_val = self.previous_state.value if self.previous_state else None
        created = self.created_at.isoformat() if self.created_at else None
        updated = self.updated_at.isoformat() if self.updated_at else None
        last_ia = self.last_interaction_at
        last_ia_fmt = last_ia.isoformat() if last_ia else None
        return {
            "id": self.id,
            "call_id": self.call_id,
            "customer_id": self.customer_id,
            "appointment_id": self.appointment_id,
            "status": status_val,
            "current_state": curr_val,
            "previous_state": prev_val,
            "context": self.context,
            "turn_count": self.turn_count,
            "needs_human": self.needs_human,
            "is_emergency": self.is_emergency,
            "created_at": created,
            "updated_at": updated,
            "last_interaction_at": last_ia_fmt,
        }
