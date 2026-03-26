"""
Google Calendar integration.

Creates calendar events when appointments are successfully scheduled.
Uses service account credentials from GOOGLE_CREDENTIALS_FILE or
GOOGLE_APPLICATION_CREDENTIALS. If not set, event creation is skipped.
"""
from datetime import datetime, timedelta
from typing import Optional, Any

from app.config.settings import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Lazy imports to avoid requiring google packages when not used
_creds: Optional[Any] = None


def _get_credentials():
    """Load credentials from file if configured."""
    global _creds
    if _creds is not None:
        return _creds
    path = getattr(settings, "google_credentials_file", None) or ""
    if not path:
        import os
        path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not path:
        return None
    try:
        from google.oauth2 import service_account
        _creds = service_account.Credentials.from_service_account_file(
            path,
            scopes=["https://www.googleapis.com/auth/calendar.events"],
        )
        return _creds
    except Exception as e:
        logger.warning(
            "google_calendar_credentials_failed",
            path=path,
            error=str(e),
        )
        return None


def create_calendar_event(
    summary: str,
    start_time: datetime,
    duration_minutes: int = 60,
    calendar_id: str = "primary",
    description: Optional[str] = None,
) -> Optional[str]:
    """
    Create a Google Calendar event.

    Args:
        summary: Event title (e.g. "Leak Repair – Michael Weber").
        start_time: datetime (timezone-aware or naive; stored as-is).
        duration_minutes: Event length in minutes.
        calendar_id: Calendar ID (default "primary" for primary calendar).
        description: Optional event description.

    Returns:
        Event ID if created, None if skipped or failed.
    """
    creds = _get_credentials()
    if not creds:
        logger.debug("google_calendar_skipped", reason="no_credentials")
        return None

    try:
        from googleapiclient.discovery import build
    except ImportError:
        logger.warning(
            "google_calendar_skipped",
            reason="google-api-python-client not installed",
        )
        return None

    try:
        service = build("calendar", "v3", credentials=creds)
        end_time = start_time + timedelta(minutes=duration_minutes)
        # API expects RFC3339 with timezone
        start_str = start_time.isoformat()
        if start_time.tzinfo is None:
            start_str += "Z"
        end_str = end_time.isoformat()
        if end_time.tzinfo is None:
            end_str += "Z"

        event = {
            "summary": summary,
            "start": {"dateTime": start_str},
            "end": {"dateTime": end_str},
        }
        if description:
            event["description"] = description

        created = service.events().insert(
            calendarId=calendar_id,
            body=event,
        ).execute()
        event_id = created.get("id")
        logger.info(
            "google_calendar_event_created",
            event_id=event_id,
            summary=summary,
            start=start_str,
        )
        return event_id
    except Exception as e:
        logger.warning(
            "google_calendar_event_failed",
            summary=summary,
            error=str(e),
        )
        return None
