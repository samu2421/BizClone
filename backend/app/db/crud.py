"""
CRUD operations for database models.
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from datetime import datetime, timezone

from app.models import (
    Customer, Call, Transcript, CallEvent, CallStatus, CallDirection,
    Appointment, AppointmentStatus, UrgencyLevel,
    ConversationStateModel, ConversationStatus, ConversationState,
    Service, Policy, FAQ
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Customer CRUD Operations
# ============================================================================

def get_customer_by_phone(db: Session, phone_number: str) -> Optional[Customer]:
    """Get customer by phone number."""
    return db.query(Customer).filter(Customer.phone_number == phone_number).first()


def get_customer_by_id(db: Session, customer_id: str) -> Optional[Customer]:
    """Get customer by ID."""
    return db.query(Customer).filter(Customer.id == customer_id).first()


def create_customer(
    db: Session,
    phone_number: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    **kwargs
) -> Customer:
    """Create a new customer."""
    customer = Customer(
        phone_number=phone_number,
        name=name,
        email=email,
        **kwargs
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    logger.info("customer_created", customer_id=customer.id, phone=phone_number)
    return customer


def update_customer(db: Session, customer_id: str, **kwargs) -> Optional[Customer]:
    """Update customer information."""
    customer = get_customer_by_id(db, customer_id)
    if customer:
        for key, value in kwargs.items():
            if hasattr(customer, key):
                setattr(customer, key, value)
        customer.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(customer)
        logger.info("customer_updated", customer_id=customer_id)
    return customer


def get_or_create_customer(db: Session, phone_number: str, **kwargs) -> Customer:
    """Get existing customer or create new one."""
    customer = get_customer_by_phone(db, phone_number)
    if not customer:
        customer = create_customer(db, phone_number, **kwargs)
    return customer


# ============================================================================
# Call CRUD Operations
# ============================================================================

def get_call_by_sid(db: Session, call_sid: str) -> Optional[Call]:
    """Get call by Twilio Call SID."""
    return db.query(Call).filter(Call.call_sid == call_sid).first()


def get_call_by_id(db: Session, call_id: str) -> Optional[Call]:
    """Get call by ID."""
    return db.query(Call).filter(Call.id == call_id).first()


def create_call(
    db: Session,
    call_sid: str,
    customer_id: str,
    from_number: str,
    to_number: str,
    direction: CallDirection,
    **kwargs
) -> Call:
    """Create a new call record."""
    call = Call(
        call_sid=call_sid,
        customer_id=customer_id,
        from_number=from_number,
        to_number=to_number,
        direction=direction,
        **kwargs
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    logger.info("call_created", call_id=call.id, call_sid=call_sid)
    return call


def update_call(db: Session, call_id: str, **kwargs) -> Optional[Call]:
    """Update call information."""
    call = get_call_by_id(db, call_id)
    if call:
        for key, value in kwargs.items():
            if hasattr(call, key):
                setattr(call, key, value)
        call.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(call)
        logger.info("call_updated", call_id=call_id)
    return call


def update_call_by_sid(db: Session, call_sid: str, **kwargs) -> Optional[Call]:
    """Update call by Call SID."""
    call = get_call_by_sid(db, call_sid)
    if call:
        for key, value in kwargs.items():
            if hasattr(call, key):
                setattr(call, key, value)
        call.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(call)
        logger.info("call_updated", call_sid=call_sid)
    return call


def get_customer_calls(
    db: Session,
    customer_id: str,
    limit: int = 10
) -> List[Call]:
    """Get recent calls for a customer."""
    return (
        db.query(Call)
        .filter(Call.customer_id == customer_id)
        .order_by(desc(Call.created_at))
        .limit(limit)
        .all()
    )


# ============================================================================
# Transcript CRUD Operations
# ============================================================================

def create_transcript(
    db: Session,
    call_id: str,
    text: str,
    language: str = "en",
    **kwargs
) -> Transcript:
    """Create a new transcript."""
    transcript = Transcript(
        call_id=call_id,
        text=text,
        language=language,
        **kwargs
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    logger.info("transcript_created", transcript_id=transcript.id, call_id=call_id)
    return transcript


def get_transcript_by_call_id(db: Session, call_id: str) -> Optional[Transcript]:
    """Get transcript for a call."""
    return db.query(Transcript).filter(Transcript.call_id == call_id).first()


# ============================================================================
# CallEvent CRUD Operations
# ============================================================================

def create_call_event(
    db: Session,
    call_id: str,
    event_type: str,
    description: Optional[str] = None,
    event_data: Optional[dict] = None
) -> CallEvent:
    """Create a new call event."""
    event = CallEvent(
        call_id=call_id,
        event_type=event_type,
        description=description,
        event_data=event_data
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info("call_event_created", event_id=event.id, call_id=call_id, event_type=event_type)
    return event


def get_call_events(db: Session, call_id: str) -> List[CallEvent]:
    """Get all events for a call."""
    return (
        db.query(CallEvent)
        .filter(CallEvent.call_id == call_id)
        .order_by(CallEvent.created_at)
        .all()
    )


# ============================================================================
# Appointment CRUD Operations
# ============================================================================

def create_appointment(
    db: Session,
    call_id: str,
    customer_id: str,
    **kwargs
) -> Appointment:
    """Create a new appointment."""
    appointment = Appointment(
        call_id=call_id,
        customer_id=customer_id,
        **kwargs
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    logger.info(
        "appointment_created",
        appointment_id=appointment.id,
        call_id=call_id
    )
    return appointment


def get_appointment_by_id(db: Session, appointment_id: str) -> Optional[Appointment]:
    """Get appointment by ID."""
    return db.query(Appointment).filter(Appointment.id == appointment_id).first()


def get_appointment_by_call_id(db: Session, call_id: str) -> Optional[Appointment]:
    """Get appointment by call ID."""
    return db.query(Appointment).filter(Appointment.call_id == call_id).first()


def get_customer_appointments(
    db: Session,
    customer_id: str,
    limit: int = 100
) -> List[Appointment]:
    """Get all appointments for a customer."""
    return (
        db.query(Appointment)
        .filter(Appointment.customer_id == customer_id)
        .order_by(desc(Appointment.created_at))
        .limit(limit)
        .all()
    )


def get_appointments_by_date_range(
    db: Session,
    start_date: datetime,
    end_date: datetime
) -> List[Appointment]:
    """Get all appointments within a date range."""
    return (
        db.query(Appointment)
        .filter(
            Appointment.scheduled_time_start >= start_date,
            Appointment.scheduled_time_start < end_date
        )
        .order_by(Appointment.scheduled_time_start)
        .all()
    )


def update_appointment(
    db: Session,
    appointment_id: str,
    **kwargs
) -> Optional[Appointment]:
    """Update appointment information."""
    appointment = get_appointment_by_id(db, appointment_id)
    if appointment:
        for key, value in kwargs.items():
            if hasattr(appointment, key):
                setattr(appointment, key, value)
        db.commit()
        db.refresh(appointment)
        logger.info("appointment_updated", appointment_id=appointment_id)
    return appointment


# ============================================================================
# Conversation State CRUD Operations
# ============================================================================

def create_conversation_state(
    db: Session,
    call_id: str,
    customer_id: str,
    **kwargs
) -> ConversationStateModel:
    """Create a new conversation state."""
    conversation = ConversationStateModel(
        call_id=call_id,
        customer_id=customer_id,
        **kwargs
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    logger.info(
        "conversation_state_created",
        conversation_id=conversation.id,
        call_id=call_id
    )
    return conversation


def get_conversation_state_by_id(
    db: Session,
    conversation_id: str
) -> Optional[ConversationStateModel]:
    """Get conversation state by ID."""
    return db.query(ConversationStateModel).filter(
        ConversationStateModel.id == conversation_id
    ).first()


def get_conversation_state_by_call_id(
    db: Session,
    call_id: str
) -> Optional[ConversationStateModel]:
    """Get conversation state by call ID."""
    return db.query(ConversationStateModel).filter(
        ConversationStateModel.call_id == call_id
    ).first()


def get_active_conversations(
    db: Session,
    limit: int = 100
) -> List[ConversationStateModel]:
    """Get all active conversations."""
    return (
        db.query(ConversationStateModel)
        .filter(ConversationStateModel.status == ConversationStatus.ACTIVE)
        .order_by(desc(ConversationStateModel.last_interaction_at))
        .limit(limit)
        .all()
    )


def update_conversation_state(
    db: Session,
    conversation_id: str,
    **kwargs
) -> Optional[ConversationStateModel]:
    """Update conversation state."""
    conversation = get_conversation_state_by_id(db, conversation_id)
    if conversation:
        for key, value in kwargs.items():
            if hasattr(conversation, key):
                setattr(conversation, key, value)
        conversation.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(conversation)
        logger.info("conversation_state_updated", conversation_id=conversation_id)
    return conversation


# ============================================================================
# Service CRUD Operations
# ============================================================================

def get_service_by_key(db: Session, service_key: str) -> Optional[Service]:
    """Get service by key."""
    return db.query(Service).filter(Service.service_key == service_key).first()


def get_all_services(db: Session) -> List[Service]:
    """Get all services."""
    return db.query(Service).all()


def create_or_update_service(
    db: Session,
    service_key: str,
    name: str,
    description: str,
    price: str
) -> Service:
    """Create or update a service."""
    service = get_service_by_key(db, service_key)
    if service:
        service.name = name
        service.description = description
        service.price = price
        logger.info("service_updated", service_key=service_key)
    else:
        service = Service(
            service_key=service_key,
            name=name,
            description=description,
            price=price
        )
        db.add(service)
        logger.info("service_created", service_key=service_key)

    db.commit()
    db.refresh(service)
    return service


# ============================================================================
# Policy CRUD Operations
# ============================================================================

def get_policy_by_key(db: Session, policy_key: str) -> Optional[Policy]:
    """Get policy by key."""
    return db.query(Policy).filter(Policy.policy_key == policy_key).first()


def get_all_policies(db: Session) -> List[Policy]:
    """Get all policies."""
    return db.query(Policy).all()


def create_or_update_policy(
    db: Session,
    policy_key: str,
    name: str,
    content: str
) -> Policy:
    """Create or update a policy."""
    policy = get_policy_by_key(db, policy_key)
    if policy:
        policy.name = name
        policy.content = content
        logger.info("policy_updated", policy_key=policy_key)
    else:
        policy = Policy(
            policy_key=policy_key,
            name=name,
            content=content
        )
        db.add(policy)
        logger.info("policy_created", policy_key=policy_key)

    db.commit()
    db.refresh(policy)
    return policy


# ============================================================================
# FAQ CRUD Operations
# ============================================================================

def get_faq_by_question(db: Session, question: str) -> Optional[FAQ]:
    """Get FAQ by exact question match."""
    return db.query(FAQ).filter(FAQ.question == question).first()


def get_all_faqs(db: Session) -> List[FAQ]:
    """Get all FAQs."""
    return db.query(FAQ).all()


def search_faqs(db: Session, search_term: str, limit: int = 10) -> List[FAQ]:
    """Search FAQs by question or answer content."""
    search_pattern = f"%{search_term}%"
    return db.query(FAQ).filter(
        (FAQ.question.ilike(search_pattern)) | (FAQ.answer.ilike(search_pattern))
    ).limit(limit).all()


def create_or_update_faq(
    db: Session,
    question: str,
    answer: str
) -> FAQ:
    """Create or update an FAQ."""
    faq = get_faq_by_question(db, question)
    if faq:
        faq.answer = answer
        logger.info("faq_updated", question=question[:50])
    else:
        faq = FAQ(
            question=question,
            answer=answer
        )
        db.add(faq)
        logger.info("faq_created", question=question[:50])

    db.commit()
    db.refresh(faq)
    return faq

