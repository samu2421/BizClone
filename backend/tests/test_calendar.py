"""
Tests for calendar service and API endpoints.
"""
import pytest
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.calendar import CalendarService
from app.models.appointment import AppointmentStatus, UrgencyLevel
from app.db.crud import (
    create_customer,
    create_call,
    create_appointment,
)
from app.db.base import Base

# Test database URL (SQLite in-memory)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def calendar_service():
    """Create calendar service instance."""
    return CalendarService()


@pytest.fixture
def sample_appointments(db_session):
    """Create sample appointments for testing."""
    # Create customer
    customer = create_customer(
        db=db_session,
        phone_number="+15551234567",
        name="Test Customer"
    )
    
    # Create call
    call = create_call(
        db=db_session,
        call_sid="TEST_CALL_001",
        customer_id=customer.id,
        from_number="+15551234567",
        to_number="+15559876543",
        direction="inbound"
    )
    
    # Create appointments for different dates
    tz = ZoneInfo("America/New_York")
    today = datetime.now(tz).date()
    
    appointments = []
    
    # Today - 2 appointments
    for i in range(2):
        start_time = datetime.combine(today, datetime.min.time()).replace(tzinfo=tz)
        start_time = start_time.replace(hour=9 + i * 2)
        end_time = start_time + timedelta(hours=1)
        
        appt = create_appointment(
            db=db_session,
            call_id=call.id,
            customer_id=customer.id,
            scheduled_time_start=start_time,
            scheduled_time_end=end_time,
            status=AppointmentStatus.SCHEDULED,
            urgency=UrgencyLevel.MEDIUM,
            service_type="repair"
        )
        appointments.append(appt)
    
    # Tomorrow - 1 appointment
    tomorrow = today + timedelta(days=1)
    start_time = datetime.combine(tomorrow, datetime.min.time()).replace(tzinfo=tz)
    start_time = start_time.replace(hour=10)
    end_time = start_time + timedelta(hours=1)
    
    appt = create_appointment(
        db=db_session,
        call_id=call.id,
        customer_id=customer.id,
        scheduled_time_start=start_time,
        scheduled_time_end=end_time,
        status=AppointmentStatus.CONFIRMED,
        urgency=UrgencyLevel.HIGH,
        service_type="installation"
    )
    appointments.append(appt)
    
    # Next week - 1 canceled appointment (should be filtered out)
    next_week = today + timedelta(days=7)
    start_time = datetime.combine(next_week, datetime.min.time()).replace(tzinfo=tz)
    start_time = start_time.replace(hour=14)
    end_time = start_time + timedelta(hours=1)
    
    appt = create_appointment(
        db=db_session,
        call_id=call.id,
        customer_id=customer.id,
        scheduled_time_start=start_time,
        scheduled_time_end=end_time,
        status=AppointmentStatus.CANCELED,
        urgency=UrgencyLevel.LOW,
        service_type="maintenance"
    )
    appointments.append(appt)
    
    return appointments


class TestCalendarService:
    """Test calendar service functionality."""
    
    def test_get_day_view(self, db_session, calendar_service, sample_appointments):
        """Test getting day view."""
        today = date.today()

        day_view = calendar_service.get_day_view(db_session, today)

        assert day_view["date"] == today
        assert day_view["total_appointments"] >= 1  # At least 1 scheduled for today
        assert day_view["available_slots"] >= 0
        assert len(day_view["appointments"]) >= 1
    
    def test_get_day_view_empty(self, db_session, calendar_service):
        """Test getting day view for a day with no appointments."""
        future_date = date.today() + timedelta(days=30)
        
        day_view = calendar_service.get_day_view(db_session, future_date)
        
        assert day_view["date"] == future_date
        assert day_view["total_appointments"] == 0
        assert day_view["available_slots"] == 8  # Max daily appointments
        assert len(day_view["appointments"]) == 0
    
    def test_get_week_view(self, db_session, calendar_service, sample_appointments):
        """Test getting week view."""
        today = date.today()

        week_view = calendar_service.get_week_view(db_session, today)

        assert week_view["start_date"] == today
        assert week_view["end_date"] == today + timedelta(days=6)
        assert len(week_view["days"]) == 7
        assert week_view["total_appointments"] >= 1  # At least 1 appointment

    def test_get_month_view(self, db_session, calendar_service, sample_appointments):
        """Test getting month view."""
        today = date.today()

        month_view = calendar_service.get_month_view(
            db_session,
            today.year,
            today.month
        )

        assert month_view["year"] == today.year
        assert month_view["month"] == today.month
        assert len(month_view["days"]) >= 28  # At least 28 days in a month
        assert month_view["total_appointments"] >= 2

    def test_get_upcoming_appointments(
        self,
        db_session,
        calendar_service,
        sample_appointments
    ):
        """Test getting upcoming appointments."""
        appointments = calendar_service.get_upcoming_appointments(
            db_session,
            days_ahead=7,
            limit=50
        )

        # Should get at least 1 appointment
        # Canceled appointment should be filtered out
        assert len(appointments) >= 1

        # Should be sorted by time
        for i in range(len(appointments) - 1):
            time1 = appointments[i].scheduled_time_start or appointments[i].created_at
            time2 = appointments[i + 1].scheduled_time_start or appointments[i + 1].created_at
            assert time1 <= time2

    def test_get_appointments_by_status(
        self,
        db_session,
        calendar_service,
        sample_appointments
    ):
        """Test filtering appointments by status."""
        scheduled = calendar_service.get_appointments_by_status(
            db_session,
            AppointmentStatus.SCHEDULED
        )

        assert len(scheduled) == 2  # 2 scheduled appointments
        assert all(appt.status == AppointmentStatus.SCHEDULED for appt in scheduled)

        confirmed = calendar_service.get_appointments_by_status(
            db_session,
            AppointmentStatus.CONFIRMED
        )

        assert len(confirmed) == 1  # 1 confirmed appointment

        canceled = calendar_service.get_appointments_by_status(
            db_session,
            AppointmentStatus.CANCELED
        )

        assert len(canceled) == 1  # 1 canceled appointment

    def test_get_availability(self, db_session, calendar_service, sample_appointments):
        """Test getting availability for a date."""
        today = date.today()

        availability = calendar_service.get_availability(
            db_session,
            today,
            num_slots=8
        )

        assert availability["date"] == today
        assert "available_slots" in availability
        assert "total_slots" in availability
        assert "available_count" in availability
        assert availability["total_slots"] > 0
        # Should have some available slots
        assert availability["available_count"] >= 0

