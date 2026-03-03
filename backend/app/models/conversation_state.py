"""
Conversation state model for tracking multi-turn dialogues.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON, Integer, Boolean
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
    AWAITING_SERVICE_DETAILS = "awaiting_service_details"  # Waiting for problem description
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
    call_id = Column(String, ForeignKey("calls.id"), nullable=False, index=True, unique=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False, index=True)
    appointment_id = Column(String, ForeignKey("appointments.id"), nullable=True, index=True)
    
    # State Information
    status = Column(
        SQLEnum(ConversationStatus),
        default=ConversationStatus.ACTIVE,
        nullable=False,
        index=True
    )
    current_state = Column(
        SQLEnum(ConversationState),
        default=ConversationState.INITIAL,
        nullable=False,
        index=True
    )
    previous_state = Column(SQLEnum(ConversationState), nullable=True)
    
    # Context Data (JSON)
    context = Column(JSON, nullable=True, default=dict)
    # Context can include:
    # - missing_fields: ["date", "location"]
    # - collected_data: {"service_type": "sink_repair", "urgency": "high"}
    # - last_question: "What date works best for you?"
    # - confirmation_pending: "appointment_details"
    # - turn_count: 3
    # - last_intent: "booking"
    
    # Metadata
    turn_count = Column(Integer, default=0, nullable=False)  # Number of exchanges
    last_message = Column(Text, nullable=True)  # Last customer message
    last_response = Column(Text, nullable=True)  # Last system response
    
    # Flags
    needs_human = Column(Boolean, default=False, nullable=False)  # Escalation flag
    is_emergency = Column(Boolean, default=False, nullable=False)  # Emergency flag
    
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
    call = relationship("Call", back_populates="conversation_state", repr=False, lazy="select")
    customer = relationship("Customer", back_populates="conversation_states", repr=False, lazy="select")
    appointment = relationship("Appointment", back_populates="conversation_state", repr=False, lazy="select")
    
    def __repr__(self):
        return (
            f"<ConversationState(id={self.id}, "
            f"status={self.status}, "
            f"state={self.current_state})>"
        )
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "call_id": self.call_id,
            "customer_id": self.customer_id,
            "appointment_id": self.appointment_id,
            "status": self.status.value if self.status else None,
            "current_state": self.current_state.value if self.current_state else None,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "context": self.context,
            "turn_count": self.turn_count,
            "needs_human": self.needs_human,
            "is_emergency": self.is_emergency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_interaction_at": self.last_interaction_at.isoformat() if self.last_interaction_at else None,
        }

