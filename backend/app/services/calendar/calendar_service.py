"""
Calendar service for managing appointments and availability.
"""
from typing import List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from app.core.logging import get_logger
from app.config.settings import settings
from app.db.crud import get_appointments_by_date_range
from app.models.appointment import Appointment, AppointmentStatus
from app.services.scheduling import SchedulingService

logger = get_logger(__name__)


class CalendarService:
    """
    Service for calendar operations and appointment views.
    
    Provides:
    - Day/week/month calendar views
    - Availability checking
    - Appointment listing and filtering
    """
    
    def __init__(self):
        """Initialize calendar service."""
        self.timezone = ZoneInfo(settings.business_timezone)
        self.scheduler = SchedulingService()
    
    def get_day_view(
        self,
        db: Session,
        target_date: date
    ) -> dict:
        """
        Get calendar view for a single day.
        
        Args:
            db: Database session
            target_date: Date to view
        
        Returns:
            dict: Day view with appointments and availability
        """
        # Convert date to datetime range
        day_start = datetime.combine(target_date, datetime.min.time())
        day_start = day_start.replace(tzinfo=self.timezone)
        day_end = day_start + timedelta(days=1)
        
        # Get appointments for the day
        appointments = get_appointments_by_date_range(db, day_start, day_end)
        
        # Filter out canceled and no-show appointments
        active_appointments = [
            appt for appt in appointments
            if appt.status not in [AppointmentStatus.CANCELED, AppointmentStatus.NO_SHOW]
        ]
        
        # Calculate available slots
        available_slots = self.scheduler.max_daily_appointments - len(active_appointments)
        
        logger.info(
            "day_view_generated",
            date=target_date.isoformat(),
            total_appointments=len(active_appointments),
            available_slots=available_slots
        )
        
        return {
            "date": target_date,
            "appointments": active_appointments,
            "total_appointments": len(active_appointments),
            "available_slots": max(0, available_slots)
        }
    
    def get_week_view(
        self,
        db: Session,
        start_date: date
    ) -> dict:
        """
        Get calendar view for a week.
        
        Args:
            db: Database session
            start_date: Week start date (typically Monday)
        
        Returns:
            dict: Week view with daily breakdowns
        """
        days = []
        total_appointments = 0
        
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            day_view = self.get_day_view(db, current_date)
            days.append(day_view)
            total_appointments += day_view["total_appointments"]
        
        end_date = start_date + timedelta(days=6)
        
        logger.info(
            "week_view_generated",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            total_appointments=total_appointments
        )
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "days": days,
            "total_appointments": total_appointments
        }
    
    def get_month_view(
        self,
        db: Session,
        year: int,
        month: int
    ) -> dict:
        """
        Get calendar view for a month.
        
        Args:
            db: Database session
            year: Year
            month: Month (1-12)
        
        Returns:
            dict: Month view with daily breakdowns
        """
        # Get first and last day of month
        first_day = date(year, month, 1)
        
        # Calculate last day of month
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        
        days = []
        total_appointments = 0
        current_date = first_day
        
        while current_date <= last_day:
            day_view = self.get_day_view(db, current_date)
            days.append(day_view)
            total_appointments += day_view["total_appointments"]
            current_date += timedelta(days=1)
        
        logger.info(
            "month_view_generated",
            year=year,
            month=month,
            total_appointments=total_appointments
        )

        return {
            "year": year,
            "month": month,
            "days": days,
            "total_appointments": total_appointments
        }

    def get_availability(
        self,
        db: Session,
        target_date: date,
        num_slots: int = 8
    ) -> dict:
        """
        Get available time slots for a specific date.

        Args:
            db: Database session
            target_date: Date to check availability
            num_slots: Number of slots to return

        Returns:
            dict: Available slots for the date
        """
        # Convert date to datetime for scheduler
        start_datetime = datetime.combine(target_date, datetime.min.time())
        start_datetime = start_datetime.replace(tzinfo=self.timezone)

        # Use scheduler to find available slots
        slots = self.scheduler.find_available_slots(
            db=db,
            start_date=start_datetime,
            num_days=1,
            num_slots=num_slots
        )

        # Convert to availability format
        available_slots = []
        for slot in slots:
            available_slots.append({
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "is_available": slot.is_available
            })

        available_count = sum(1 for slot in slots if slot.is_available)

        logger.info(
            "availability_checked",
            date=target_date.isoformat(),
            total_slots=len(slots),
            available_count=available_count
        )

        return {
            "date": target_date,
            "available_slots": available_slots,
            "total_slots": len(slots),
            "available_count": available_count
        }

    def get_appointments_by_status(
        self,
        db: Session,
        status: AppointmentStatus,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Appointment]:
        """
        Get appointments filtered by status and optional date range.

        Args:
            db: Database session
            status: Appointment status to filter by
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            List[Appointment]: Filtered appointments
        """
        # Default to current month if no dates provided
        if not start_date:
            today = date.today()
            start_date = date(today.year, today.month, 1)

        if not end_date:
            # End of current month
            if start_date.month == 12:
                end_date = date(start_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1)

        # Convert to datetime
        dt_start = datetime.combine(start_date, datetime.min.time())
        dt_start = dt_start.replace(tzinfo=self.timezone)
        dt_end = datetime.combine(end_date, datetime.max.time())
        dt_end = dt_end.replace(tzinfo=self.timezone)

        # Get all appointments in range
        appointments = get_appointments_by_date_range(db, dt_start, dt_end)

        # Filter by status
        filtered = [appt for appt in appointments if appt.status == status]

        logger.info(
            "appointments_filtered_by_status",
            status=status.value,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            count=len(filtered)
        )

        return filtered

    def get_upcoming_appointments(
        self,
        db: Session,
        days_ahead: int = 7,
        limit: int = 50
    ) -> List[Appointment]:
        """
        Get upcoming appointments.

        Args:
            db: Database session
            days_ahead: Number of days to look ahead
            limit: Maximum number of appointments to return

        Returns:
            List[Appointment]: Upcoming appointments
        """
        today = date.today()
        end_date = today + timedelta(days=days_ahead)

        dt_start = datetime.combine(today, datetime.min.time())
        dt_start = dt_start.replace(tzinfo=self.timezone)
        dt_end = datetime.combine(end_date, datetime.max.time())
        dt_end = dt_end.replace(tzinfo=self.timezone)

        appointments = get_appointments_by_date_range(db, dt_start, dt_end)

        # Filter out canceled and no-show
        active = [
            appt for appt in appointments
            if appt.status not in [AppointmentStatus.CANCELED, AppointmentStatus.NO_SHOW]
        ]

        # Sort by scheduled time
        active.sort(key=lambda x: x.scheduled_time_start or x.created_at)

        logger.info(
            "upcoming_appointments_retrieved",
            days_ahead=days_ahead,
            count=len(active[:limit])
        )

        return active[:limit]

