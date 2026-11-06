"""
Scheduling Service - Manages appointment scheduling and availability.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logging import get_logger
from app.models.appointment import Appointment, AppointmentStatus, UrgencyLevel
from app.db.crud import get_appointments_by_date_range
from app.services.scheduling.validation import (
    validate_requested_time,
    enforce_future_time,
    FUTURE_BUFFER_MINUTES,
)

logger = get_logger(__name__)


@dataclass
class TimeSlot:
    """Represents an available time slot."""
    start_time: datetime
    end_time: datetime
    is_available: bool
    reason: Optional[str] = None


@dataclass
class SchedulingResult:
    """Result from scheduling operation."""
    success: bool
    appointment_id: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    message: str = ""
    suggested_slots: Optional[List[TimeSlot]] = None
    conflict_reason: Optional[str] = None


class SchedulingService:
    """
    Manages appointment scheduling and availability checking.
    
    Features:
    - Check availability for requested time slots
    - Find available time slots
    - Schedule appointments
    - Handle conflicts and double-bookings
    - Respect business hours
    - Handle emergency appointments
    """
    
    def __init__(self):
        """Initialize the scheduling service."""
        self.business_hours_start = self._parse_time(settings.business_hours_start)
        self.business_hours_end = self._parse_time(settings.business_hours_end)
        self.appointment_duration = timedelta(minutes=settings.appointment_duration_minutes)
        self.buffer_time = timedelta(minutes=settings.appointment_buffer_minutes)
        self.max_daily_appointments = settings.max_daily_appointments
        self.timezone = ZoneInfo(settings.business_timezone)
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string (HH:MM) to time object."""
        hour, minute = map(int, time_str.split(':'))
        return time(hour=hour, minute=minute)
    
    def check_availability(
        self,
        db: Session,
        requested_time: datetime,
        duration: Optional[timedelta] = None
    ) -> TimeSlot:
        """
        Check if a specific time slot is available.

        Args:
            db: Database session
            requested_time: Requested start time
            duration: Appointment duration (defaults to configured duration)

        Returns:
            TimeSlot with availability status
        """
        if duration is None:
            duration = self.appointment_duration

        end_time = requested_time + duration

        logger.info(
            "checking_availability",
            requested_time=requested_time.isoformat(),
            duration_minutes=duration.total_seconds() / 60
        )

        # ── Past-time guard ─────────────────────────────────────────
        now = datetime.now(self.timezone)
        req_tz = requested_time if requested_time.tzinfo else requested_time.replace(tzinfo=self.timezone)
        if req_tz < now:
            return TimeSlot(
                start_time=requested_time,
                end_time=end_time,
                is_available=False,
                reason="Requested time is in the past"
            )

        # Check if within business hours
        if not self._is_within_business_hours(requested_time, end_time):
            return TimeSlot(
                start_time=requested_time,
                end_time=end_time,
                is_available=False,
                reason="Outside business hours"
            )
        
        # Check for conflicts with existing appointments
        conflict = self._check_conflicts(db, requested_time, end_time)
        if conflict:
            return TimeSlot(
                start_time=requested_time,
                end_time=end_time,
                is_available=False,
                reason=f"Conflict with existing appointment: {conflict}"
            )
        
        # Check daily appointment limit
        if not self._check_daily_limit(db, requested_time):
            return TimeSlot(
                start_time=requested_time,
                end_time=end_time,
                is_available=False,
                reason="Maximum daily appointments reached"
            )
        
        return TimeSlot(
            start_time=requested_time,
            end_time=end_time,
            is_available=True
        )
    
    def find_available_slots(
        self,
        db: Session,
        start_date: datetime,
        num_days: int = 7,
        num_slots: int = 5
    ) -> List[TimeSlot]:
        """
        Find available time slots within a date range.
        
        Args:
            db: Database session
            start_date: Start searching from this date
            num_days: Number of days to search
            num_slots: Maximum number of slots to return
            
        Returns:
            List of available TimeSlots
        """
        logger.info(
            "finding_available_slots",
            start_date=start_date.isoformat(),
            num_days=num_days,
            num_slots=num_slots
        )
        
        available_slots = []
        current_date = start_date.replace(
            hour=self.business_hours_start.hour,
            minute=self.business_hours_start.minute,
            second=0,
            microsecond=0
        )

        # ── Never start searching from the past ────────────────────
        now = datetime.now(self.timezone)
        effective_now = now + timedelta(minutes=FUTURE_BUFFER_MINUTES)
        if current_date.tzinfo is None:
            effective_now_naive = effective_now.replace(tzinfo=None)
        else:
            effective_now_naive = effective_now
        if current_date < effective_now_naive:
            current_date = effective_now_naive.replace(second=0, microsecond=0)
            # If we've landed mid-day, don't reset to morning
            if current_date.time() < self.business_hours_start:
                current_date = current_date.replace(
                    hour=self.business_hours_start.hour,
                    minute=self.business_hours_start.minute,
                )

        days_checked = 0
        while len(available_slots) < num_slots and days_checked < num_days:
            # Generate slots for the current day
            day_slots = self._generate_day_slots(db, current_date)
            available_slots.extend([s for s in day_slots if s.is_available])
            
            # Move to next day
            current_date += timedelta(days=1)
            current_date = current_date.replace(
                hour=self.business_hours_start.hour,
                minute=self.business_hours_start.minute
            )
            days_checked += 1
        
        return available_slots[:num_slots]

    def schedule_appointment(
        self,
        db: Session,
        appointment: Appointment,
        requested_time: Optional[datetime] = None,
        force_emergency: bool = False
    ) -> SchedulingResult:
        """
        Schedule an appointment.

        Args:
            db: Database session
            appointment: Appointment object to schedule
            requested_time: Specific time requested (optional)
            force_emergency: Force scheduling even if conflicts exist

        Returns:
            SchedulingResult with success status and details
        """
        logger.info(
            "scheduling_appointment",
            appointment_id=appointment.id,
            requested_time=requested_time.isoformat() if requested_time else None,
            force_emergency=force_emergency
        )

        # If no specific time requested, use the appointment's requested_time_start
        if requested_time is None:
            requested_time = appointment.requested_time_start

        # ── If user provided a specific time, PRIORITIZE it ───────
        user_provided_time = requested_time is not None

        # If still no time, find next available slot
        if requested_time is None:
            now = datetime.now(self.timezone)
            available_slots = self.find_available_slots(db, now, num_days=7, num_slots=1)

            if not available_slots:
                return SchedulingResult(
                    success=False,
                    message="No available slots found in the next 7 days",
                    suggested_slots=[]
                )

            requested_time = available_slots[0].start_time
            logger.info("auto_slot_selected", slot=requested_time.isoformat())

        # ── Enforce future time (never schedule in the past) ──────
        requested_time = enforce_future_time(requested_time)

        if user_provided_time:
            logger.info(
                "requested_time_received",
                requested_time=requested_time.isoformat(),
            )

        # For emergencies, force scheduling
        if force_emergency or appointment.urgency == UrgencyLevel.EMERGENCY:
            end_time = requested_time + self.appointment_duration
            appointment.scheduled_date = requested_time.date()
            appointment.scheduled_time_start = requested_time
            appointment.scheduled_time_end = end_time
            appointment.status = AppointmentStatus.SCHEDULED

            logger.info(
                "emergency_appointment_scheduled",
                appointment_id=appointment.id,
                scheduled_time=requested_time.isoformat()
            )

            return SchedulingResult(
                success=True,
                appointment_id=appointment.id,
                scheduled_time=requested_time,
                message="Emergency appointment scheduled immediately"
            )

        # Check availability
        slot = self.check_availability(db, requested_time)

        if not slot.is_available:
            # Find alternative slots
            suggested_slots = self.find_available_slots(
                db,
                requested_time,
                num_days=7,
                num_slots=3
            )

            return SchedulingResult(
                success=False,
                message=f"Requested time not available: {slot.reason}",
                suggested_slots=suggested_slots,
                conflict_reason=slot.reason
            )

        # Schedule the appointment
        appointment.scheduled_date = requested_time.date()
        appointment.scheduled_time_start = requested_time
        appointment.scheduled_time_end = requested_time + self.appointment_duration
        appointment.status = AppointmentStatus.SCHEDULED

        logger.info(
            "appointment_scheduled",
            appointment_id=appointment.id,
            scheduled_time=requested_time.isoformat()
        )

        return SchedulingResult(
            success=True,
            appointment_id=appointment.id,
            scheduled_time=requested_time,
            message="Appointment scheduled successfully"
        )

    def _is_within_business_hours(self, start_time: datetime, end_time: datetime) -> bool:
        """Check if time slot is within business hours."""
        # Skip weekends (Saturday=5, Sunday=6)
        if start_time.weekday() >= 5:
            return False

        start_time_only = start_time.time()
        end_time_only = end_time.time()

        return (
            start_time_only >= self.business_hours_start and
            end_time_only <= self.business_hours_end
        )

    def _check_conflicts(
        self,
        db: Session,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[str]:
        """Check for scheduling conflicts."""
        # Get appointments for the day
        day_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        appointments = get_appointments_by_date_range(db, day_start, day_end)

        for appt in appointments:
            if appt.status in [AppointmentStatus.CANCELED, AppointmentStatus.NO_SHOW]:
                continue

            if not appt.scheduled_time_start or not appt.scheduled_time_end:
                continue

            # Normalize timezone info for comparison
            appt_start_time = appt.scheduled_time_start
            appt_end_time = appt.scheduled_time_end

            # If one is timezone-aware and the other isn't, make them compatible
            if start_time.tzinfo is not None and appt_start_time.tzinfo is None:
                appt_start_time = appt_start_time.replace(tzinfo=start_time.tzinfo)
                appt_end_time = appt_end_time.replace(tzinfo=start_time.tzinfo)
            elif start_time.tzinfo is None and appt_start_time.tzinfo is not None:
                appt_start_time = appt_start_time.replace(tzinfo=None)
                appt_end_time = appt_end_time.replace(tzinfo=None)

            # Check for overlap (with buffer time)
            appt_start = appt_start_time - self.buffer_time
            appt_end = appt_end_time + self.buffer_time

            if (start_time < appt_end and end_time > appt_start):
                return f"Appointment {appt.id} at {appt.scheduled_time_start.strftime('%H:%M')}"

        return None

    def _check_daily_limit(self, db: Session, requested_time: datetime) -> bool:
        """Check if daily appointment limit is reached."""
        day_start = requested_time.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        appointments = get_appointments_by_date_range(db, day_start, day_end)

        # Count non-canceled appointments
        active_count = sum(
            1 for appt in appointments
            if appt.status not in [AppointmentStatus.CANCELED, AppointmentStatus.NO_SHOW]
        )

        return active_count < self.max_daily_appointments

    def _generate_day_slots(self, db: Session, date: datetime) -> List[TimeSlot]:
        """Generate all possible time slots for a given day."""
        slots = []
        current_time = date.replace(
            hour=self.business_hours_start.hour,
            minute=self.business_hours_start.minute,
            second=0,
            microsecond=0
        )

        end_of_day = date.replace(
            hour=self.business_hours_end.hour,
            minute=self.business_hours_end.minute,
            second=0,
            microsecond=0
        )

        while current_time + self.appointment_duration <= end_of_day:
            slot = self.check_availability(db, current_time)
            slots.append(slot)
            current_time += self.appointment_duration + self.buffer_time

        return slots

