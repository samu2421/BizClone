"""External service integrations (e.g. Google Calendar)."""
from app.services.integrations.google_calendar import create_calendar_event

__all__ = ["create_calendar_event"]
