"""
Tests for the Scheduling Service.
"""
import pytest
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.scheduling import SchedulingService, SchedulingResult, TimeSlot
from app.models.appointment import Appointment, AppointmentStatus, UrgencyLevel
from app.db.crud import create_appointment, create_customer, create_call
from app.db.base import Base

# Test database URL (SQLite in-memory)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_customer(db_session):
    """Create a test customer."""
    return create_customer(db_session, phone_number="+15551234567", name="Test Customer")


@pytest.fixture
def test_call(db_session, test_customer):
    """Create a test call."""
    from app.models.call import CallDirection
    return create_call(
        db_session,
        call_sid="test_call_sid_123",
        customer_id=test_customer.id,
        from_number="+15551234567",
        to_number="+15559876543",
        direction=CallDirection.INBOUND
    )


@pytest.fixture
def scheduler():
    """Create a SchedulingService instance."""
    return SchedulingService()


@pytest.fixture
def test_timezone():
    """Get test timezone."""
    return ZoneInfo("America/New_York")


@pytest.fixture
def business_day(test_timezone):
    """Create a datetime for a business day (Monday at 9 AM)."""
    # Get next Monday
    now = datetime.now(test_timezone)
    days_ahead = 0 - now.weekday()  # Monday is 0
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    next_monday = now + timedelta(days=days_ahead)
    return next_monday.replace(hour=9, minute=0, second=0, microsecond=0)


class TestSchedulingService:
    """Test suite for SchedulingService."""
    
    def test_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler is not None
        assert scheduler.business_hours_start == time(8, 0)
        assert scheduler.business_hours_end == time(18, 0)
        assert scheduler.appointment_duration == timedelta(minutes=60)
        assert scheduler.buffer_time == timedelta(minutes=15)
        assert scheduler.max_daily_appointments == 8
    
    def test_parse_time(self, scheduler):
        """Test time string parsing."""
        parsed = scheduler._parse_time("14:30")
        assert parsed == time(14, 30)
        
        parsed = scheduler._parse_time("08:00")
        assert parsed == time(8, 0)
    
    def test_is_within_business_hours_valid(self, scheduler, business_day):
        """Test business hours check for valid time."""
        start_time = business_day.replace(hour=10, minute=0)
        end_time = start_time + timedelta(hours=1)
        
        assert scheduler._is_within_business_hours(start_time, end_time) is True
    
    def test_is_within_business_hours_too_early(self, scheduler, business_day):
        """Test business hours check for time too early."""
        start_time = business_day.replace(hour=7, minute=0)
        end_time = start_time + timedelta(hours=1)
        
        assert scheduler._is_within_business_hours(start_time, end_time) is False
    
    def test_is_within_business_hours_too_late(self, scheduler, business_day):
        """Test business hours check for time too late."""
        start_time = business_day.replace(hour=17, minute=30)
        end_time = start_time + timedelta(hours=1)
        
        assert scheduler._is_within_business_hours(start_time, end_time) is False
    
    def test_is_within_business_hours_weekend(self, scheduler, business_day):
        """Test business hours check for weekend."""
        # Saturday
        saturday = business_day + timedelta(days=5)
        start_time = saturday.replace(hour=10, minute=0)
        end_time = start_time + timedelta(hours=1)
        
        assert scheduler._is_within_business_hours(start_time, end_time) is False
    
    def test_check_availability_available(self, scheduler, business_day, db_session):
        """Test availability check for available slot."""
        slot = scheduler.check_availability(db_session, business_day)
        
        assert slot.is_available is True
        assert slot.start_time == business_day
        assert slot.end_time == business_day + timedelta(hours=1)
        assert slot.reason is None
    
    def test_check_availability_outside_hours(self, scheduler, business_day, db_session):
        """Test availability check for time outside business hours."""
        early_time = business_day.replace(hour=7, minute=0)
        slot = scheduler.check_availability(db_session, early_time)
        
        assert slot.is_available is False
        assert slot.reason == "Outside business hours"
    
    def test_check_availability_with_conflict(self, scheduler, business_day, db_session, test_customer, test_call):
        """Test availability check with existing appointment."""
        # Create an existing appointment
        existing_appt = create_appointment(
            db_session,
            call_id=test_call.id,
            customer_id=test_customer.id,
            scheduled_time_start=business_day,
            scheduled_time_end=business_day + timedelta(hours=1),
            status=AppointmentStatus.SCHEDULED
        )
        db_session.commit()
        
        # Try to book at the same time
        slot = scheduler.check_availability(db_session, business_day)
        
        assert slot.is_available is False
        assert "Conflict" in slot.reason
    
    def test_find_available_slots(self, scheduler, business_day, db_session):
        """Test finding available slots."""
        slots = scheduler.find_available_slots(
            db_session,
            business_day,
            num_days=3,
            num_slots=5
        )
        
        assert len(slots) > 0
        assert all(slot.is_available for slot in slots)
        assert all(isinstance(slot, TimeSlot) for slot in slots)
    
    def test_find_available_slots_limited(self, scheduler, business_day, db_session):
        """Test finding limited number of slots."""
        slots = scheduler.find_available_slots(
            db_session,
            business_day,
            num_days=1,
            num_slots=3
        )
        
        assert len(slots) <= 3

    def test_schedule_appointment_success(self, scheduler, business_day, db_session, test_customer, test_call):
        """Test successful appointment scheduling."""
        # Create appointment
        appointment = create_appointment(
            db_session,
            call_id=test_call.id,
            customer_id=test_customer.id,
            requested_time_start=business_day,
            status=AppointmentStatus.PENDING
        )
        db_session.commit()

        # Schedule it
        result = scheduler.schedule_appointment(
            db_session,
            appointment,
            requested_time=business_day
        )

        assert result.success is True
        assert result.appointment_id == appointment.id
        assert result.scheduled_time == business_day
        assert appointment.status == AppointmentStatus.SCHEDULED
        assert appointment.scheduled_time_start == business_day

    def test_schedule_appointment_emergency(self, scheduler, business_day, db_session, test_customer, test_call):
        """Test emergency appointment scheduling (force scheduling)."""
        # Create emergency appointment
        appointment = create_appointment(
            db_session,
            call_id=test_call.id,
            customer_id=test_customer.id,
            urgency=UrgencyLevel.EMERGENCY,
            status=AppointmentStatus.PENDING
        )
        db_session.commit()

        # Schedule it with force_emergency
        result = scheduler.schedule_appointment(
            db_session,
            appointment,
            requested_time=business_day,
            force_emergency=True
        )

        assert result.success is True
        assert "emergency" in result.message.lower()
        assert appointment.status == AppointmentStatus.SCHEDULED

    def test_schedule_appointment_conflict(self, scheduler, business_day, db_session, test_customer, test_call):
        """Test scheduling with conflict returns alternatives."""
        # Create existing appointment
        existing_appt = create_appointment(
            db_session,
            call_id=test_call.id,
            customer_id=test_customer.id,
            scheduled_time_start=business_day,
            scheduled_time_end=business_day + timedelta(hours=1),
            status=AppointmentStatus.SCHEDULED
        )
        db_session.commit()

        # Try to schedule another at the same time
        new_call = Mock()
        new_call.id = "new_call_123"
        new_appointment = create_appointment(
            db_session,
            call_id=new_call.id,
            customer_id=test_customer.id,
            requested_time_start=business_day,
            status=AppointmentStatus.PENDING
        )
        db_session.commit()

        result = scheduler.schedule_appointment(
            db_session,
            new_appointment,
            requested_time=business_day
        )

        assert result.success is False
        assert result.conflict_reason is not None
        assert result.suggested_slots is not None
        assert len(result.suggested_slots) > 0

    def test_schedule_appointment_auto_find_slot(self, scheduler, business_day, db_session, test_customer, test_call):
        """Test automatic slot finding when no time specified."""
        # Create appointment without specific time
        appointment = create_appointment(
            db_session,
            call_id=test_call.id,
            customer_id=test_customer.id,
            status=AppointmentStatus.PENDING
        )
        db_session.commit()

        # Schedule without specifying time
        result = scheduler.schedule_appointment(
            db_session,
            appointment,
            requested_time=None
        )

        assert result.success is True
        assert result.scheduled_time is not None
        assert appointment.scheduled_time_start is not None

    def test_check_daily_limit(self, scheduler, business_day, db_session, test_customer, test_call):
        """Test daily appointment limit checking."""
        # Create max appointments for the day
        for i in range(8):  # max_daily_appointments = 8
            time_slot = business_day + timedelta(hours=i)
            create_appointment(
                db_session,
                call_id=f"call_{i}",
                customer_id=test_customer.id,
                scheduled_time_start=time_slot,
                scheduled_time_end=time_slot + timedelta(hours=1),
                status=AppointmentStatus.SCHEDULED
            )
        db_session.commit()

        # Check if limit is reached
        result = scheduler._check_daily_limit(db_session, business_day)
        assert result is False

    def test_check_daily_limit_with_canceled(self, scheduler, business_day, db_session, test_customer):
        """Test daily limit doesn't count canceled appointments."""
        # Create some canceled appointments
        for i in range(5):
            time_slot = business_day + timedelta(hours=i)
            create_appointment(
                db_session,
                call_id=f"call_{i}",
                customer_id=test_customer.id,
                scheduled_time_start=time_slot,
                scheduled_time_end=time_slot + timedelta(hours=1),
                status=AppointmentStatus.CANCELED
            )
        db_session.commit()

        # Should still have room
        result = scheduler._check_daily_limit(db_session, business_day)
        assert result is True

    def test_generate_day_slots(self, scheduler, business_day, db_session):
        """Test generating all slots for a day."""
        slots = scheduler._generate_day_slots(db_session, business_day)

        assert len(slots) > 0
        # Should have multiple slots within business hours
        assert all(isinstance(slot, TimeSlot) for slot in slots)
        # All slots should be within business hours
        for slot in slots:
            assert slot.start_time.time() >= scheduler.business_hours_start
            assert slot.end_time.time() <= scheduler.business_hours_end

    def test_check_conflicts_with_buffer(self, scheduler, business_day, db_session, test_customer, test_call):
        """Test conflict detection includes buffer time."""
        # Create appointment at 10:00-11:00
        existing_time = business_day.replace(hour=10, minute=0)
        create_appointment(
            db_session,
            call_id=test_call.id,
            customer_id=test_customer.id,
            scheduled_time_start=existing_time,
            scheduled_time_end=existing_time + timedelta(hours=1),
            status=AppointmentStatus.SCHEDULED
        )
        db_session.commit()

        # Try to book at 11:00 (should conflict due to 15-min buffer)
        new_time = existing_time + timedelta(hours=1)
        conflict = scheduler._check_conflicts(
            db_session,
            new_time,
            new_time + timedelta(hours=1)
        )

        assert conflict is not None

    def test_no_conflict_with_sufficient_gap(self, scheduler, business_day, db_session, test_customer, test_call):
        """Test no conflict when sufficient gap exists."""
        # Create appointment at 10:00-11:00
        existing_time = business_day.replace(hour=10, minute=0)
        create_appointment(
            db_session,
            call_id=test_call.id,
            customer_id=test_customer.id,
            scheduled_time_start=existing_time,
            scheduled_time_end=existing_time + timedelta(hours=1),
            status=AppointmentStatus.SCHEDULED
        )
        db_session.commit()

        # Try to book at 11:30 (30 min gap > 15 min buffer)
        new_time = existing_time + timedelta(hours=1, minutes=30)
        conflict = scheduler._check_conflicts(
            db_session,
            new_time,
            new_time + timedelta(hours=1)
        )

        assert conflict is None

