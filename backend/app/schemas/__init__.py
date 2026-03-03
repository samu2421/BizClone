"""
Pydantic schemas for API requests and responses.
"""
from app.schemas.health import HealthCheck, ServiceStatus
from app.schemas.twilio import TwilioInboundCall, TwilioCallStatus, TwiMLResponse
from app.schemas.calendar import (
    AppointmentBase,
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    CalendarDayView,
    CalendarWeekView,
    CalendarMonthView,
    AvailableSlot,
    AvailabilityResponse,
)

__all__ = [
    "HealthCheck",
    "ServiceStatus",
    "TwilioInboundCall",
    "TwilioCallStatus",
    "TwiMLResponse",
    "AppointmentBase",
    "AppointmentCreate",
    "AppointmentUpdate",
    "AppointmentResponse",
    "CalendarDayView",
    "CalendarWeekView",
    "CalendarMonthView",
    "AvailableSlot",
    "AvailabilityResponse",
]
