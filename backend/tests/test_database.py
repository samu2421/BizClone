"""
Tests for database models and CRUD operations.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from app.db.base import Base
from app.models import Customer, Call, Transcript, CallEvent, CallStatus, CallDirection
from app.db.crud import (
    get_customer_by_phone,
    create_customer,
    get_or_create_customer,
    create_call,
    get_call_by_sid,
    update_call_by_sid,
    get_customer_calls,
    create_transcript,
    get_transcript_by_call_id,
    create_call_event,
    get_call_events,
)


# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ============================================================================
# Customer Tests
# ============================================================================

def test_create_customer(db_session):
    """Test creating a customer."""
    customer = create_customer(
        db_session,
        phone_number="+15551234567",
        name="John Doe",
        email="john@example.com"
    )
    
    assert customer.id is not None
    assert customer.phone_number == "+15551234567"
    assert customer.name == "John Doe"
    assert customer.email == "john@example.com"
    assert customer.is_active is True
    assert customer.total_calls == 0


def test_get_customer_by_phone(db_session):
    """Test retrieving customer by phone number."""
    # Create customer
    created = create_customer(db_session, phone_number="+15551234567", name="Jane Doe")
    
    # Retrieve customer
    retrieved = get_customer_by_phone(db_session, "+15551234567")
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.phone_number == "+15551234567"


def test_get_or_create_customer_existing(db_session):
    """Test get_or_create with existing customer."""
    # Create customer
    created = create_customer(db_session, phone_number="+15551234567", name="John Doe")
    
    # Get or create should return existing
    retrieved = get_or_create_customer(db_session, phone_number="+15551234567")
    
    assert retrieved.id == created.id
    assert retrieved.name == "John Doe"


def test_get_or_create_customer_new(db_session):
    """Test get_or_create with new customer."""
    customer = get_or_create_customer(
        db_session,
        phone_number="+15559876543",
        name="New Customer"
    )
    
    assert customer.id is not None
    assert customer.phone_number == "+15559876543"
    assert customer.name == "New Customer"


# ============================================================================
# Call Tests
# ============================================================================

def test_create_call(db_session):
    """Test creating a call record."""
    # Create customer first
    customer = create_customer(db_session, phone_number="+15551234567")
    
    # Create call
    call = create_call(
        db_session,
        call_sid="CA1234567890abcdef",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559999999",
        direction=CallDirection.INBOUND,
        status=CallStatus.RINGING
    )
    
    assert call.id is not None
    assert call.call_sid == "CA1234567890abcdef"
    assert call.customer_id == customer.id
    assert call.direction == CallDirection.INBOUND
    assert call.status == CallStatus.RINGING


def test_get_call_by_sid(db_session):
    """Test retrieving call by SID."""
    customer = create_customer(db_session, phone_number="+15551234567")
    created = create_call(
        db_session,
        call_sid="CA1234567890abcdef",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559999999",
        direction=CallDirection.INBOUND
    )
    
    retrieved = get_call_by_sid(db_session, "CA1234567890abcdef")
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.call_sid == "CA1234567890abcdef"


def test_update_call_by_sid(db_session):
    """Test updating call by SID."""
    customer = create_customer(db_session, phone_number="+15551234567")
    call = create_call(
        db_session,
        call_sid="CA1234567890abcdef",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559999999",
        direction=CallDirection.INBOUND
    )

    # Update call
    updated = update_call_by_sid(
        db_session,
        call_sid="CA1234567890abcdef",
        status=CallStatus.COMPLETED,
        duration_seconds=120,
        recording_url="https://example.com/recording.mp3"
    )

    assert updated is not None
    assert updated.status == CallStatus.COMPLETED
    assert updated.duration_seconds == 120
    assert updated.recording_url == "https://example.com/recording.mp3"


def test_get_customer_calls(db_session):
    """Test retrieving customer calls."""
    customer = create_customer(db_session, phone_number="+15551234567")

    # Create multiple calls
    call1 = create_call(
        db_session,
        call_sid="CA111",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559999999",
        direction=CallDirection.INBOUND
    )
    call2 = create_call(
        db_session,
        call_sid="CA222",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559999999",
        direction=CallDirection.INBOUND
    )

    # Get customer calls
    calls = get_customer_calls(db_session, customer.id, limit=10)

    assert len(calls) == 2
    # Should be ordered by created_at descending (most recent first)
    assert calls[0].call_sid == "CA222"
    assert calls[1].call_sid == "CA111"


# ============================================================================
# Transcript Tests
# ============================================================================

def test_create_transcript(db_session):
    """Test creating a transcript."""
    customer = create_customer(db_session, phone_number="+15551234567")
    call = create_call(
        db_session,
        call_sid="CA1234567890abcdef",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559999999",
        direction=CallDirection.INBOUND
    )

    transcript = create_transcript(
        db_session,
        call_id=call.id,
        text="Hello, I need a plumber for a leaky faucet.",
        language="en",
        confidence=0.95
    )

    assert transcript.id is not None
    assert transcript.call_id == call.id
    assert transcript.text == "Hello, I need a plumber for a leaky faucet."
    assert transcript.language == "en"
    assert transcript.confidence == 0.95


def test_get_transcript_by_call_id(db_session):
    """Test retrieving transcript by call ID."""
    customer = create_customer(db_session, phone_number="+15551234567")
    call = create_call(
        db_session,
        call_sid="CA1234567890abcdef",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559999999",
        direction=CallDirection.INBOUND
    )

    created = create_transcript(
        db_session,
        call_id=call.id,
        text="Test transcript"
    )

    retrieved = get_transcript_by_call_id(db_session, call.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.text == "Test transcript"


# ============================================================================
# CallEvent Tests
# ============================================================================

def test_create_call_event(db_session):
    """Test creating a call event."""
    customer = create_customer(db_session, phone_number="+15551234567")
    call = create_call(
        db_session,
        call_sid="CA1234567890abcdef",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559999999",
        direction=CallDirection.INBOUND
    )

    event = create_call_event(
        db_session,
        call_id=call.id,
        event_type="call_received",
        description="Inbound call received",
        event_data={"from_city": "San Francisco", "from_state": "CA"}
    )

    assert event.id is not None
    assert event.call_id == call.id
    assert event.event_type == "call_received"
    assert event.description == "Inbound call received"
    assert event.event_data["from_city"] == "San Francisco"


def test_get_call_events(db_session):
    """Test retrieving call events."""
    customer = create_customer(db_session, phone_number="+15551234567")
    call = create_call(
        db_session,
        call_sid="CA1234567890abcdef",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559999999",
        direction=CallDirection.INBOUND
    )

    # Create multiple events
    event1 = create_call_event(
        db_session,
        call_id=call.id,
        event_type="call_received",
        description="Call received"
    )
    event2 = create_call_event(
        db_session,
        call_id=call.id,
        event_type="recording_completed",
        description="Recording completed"
    )

    # Get events
    events = get_call_events(db_session, call.id)

    assert len(events) == 2
    # Should be ordered by created_at ascending
    assert events[0].event_type == "call_received"
    assert events[1].event_type == "recording_completed"


# ============================================================================
# Relationship Tests
# ============================================================================

def test_customer_calls_relationship(db_session):
    """Test customer-calls relationship."""
    customer = create_customer(db_session, phone_number="+15551234567")

    call1 = create_call(
        db_session,
        call_sid="CA111",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559999999",
        direction=CallDirection.INBOUND
    )
    call2 = create_call(
        db_session,
        call_sid="CA222",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559999999",
        direction=CallDirection.INBOUND
    )

    # Refresh to load relationships
    db_session.refresh(customer)

    assert len(customer.calls) == 2


def test_call_transcript_relationship(db_session):
    """Test call-transcript relationship."""
    customer = create_customer(db_session, phone_number="+15551234567")
    call = create_call(
        db_session,
        call_sid="CA1234567890abcdef",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559999999",
        direction=CallDirection.INBOUND
    )

    transcript = create_transcript(
        db_session,
        call_id=call.id,
        text="Test transcript"
    )

    # Refresh to load relationships
    db_session.refresh(call)

    assert len(call.transcripts) == 1
    assert call.transcripts[0].text == "Test transcript"


def test_call_events_relationship(db_session):
    """Test call-events relationship."""
    customer = create_customer(db_session, phone_number="+15551234567")
    call = create_call(
        db_session,
        call_sid="CA1234567890abcdef",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559999999",
        direction=CallDirection.INBOUND
    )

    event1 = create_call_event(db_session, call_id=call.id, event_type="call_received")
    event2 = create_call_event(db_session, call_id=call.id, event_type="call_completed")

    # Refresh to load relationships
    db_session.refresh(call)

    assert len(call.events) == 2

