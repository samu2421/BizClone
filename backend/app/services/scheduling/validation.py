"""
Scheduling validation layer — prevents past-time bookings and enforces
business-hour constraints on requested appointment times.

This module is a pure validation utility. It does NOT modify any existing
scheduling, calendar, or database logic.
"""
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from app.config.settings import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Default buffer: refuse any slot closer than this many minutes from "now"
FUTURE_BUFFER_MINUTES = 30


@dataclass
class ValidationResult:
    """Result of a time-slot validation check."""
    is_valid: bool
    reason: Optional[str] = None
    corrected_time: Optional[datetime] = None


def _get_timezone() -> ZoneInfo:
    return ZoneInfo(settings.business_timezone)


def _business_hours() -> tuple[time, time]:
    """Return (start, end) as ``datetime.time`` objects."""
    sh, sm = map(int, settings.business_hours_start.split(":"))
    eh, em = map(int, settings.business_hours_end.split(":"))
    return time(sh, sm), time(eh, em)


# ── Public API ────────────────────────────────────────────────────────────────

def validate_requested_time(
    requested_dt: datetime,
    buffer_minutes: int = FUTURE_BUFFER_MINUTES,
) -> ValidationResult:
    """
    Validate a caller-requested datetime.

    Checks:
      1. Not in the past (with configurable buffer).
      2. Within business hours (Mon-Fri, configured start/end).

    Returns a ``ValidationResult`` with ``is_valid=True`` if the slot passes
    all checks, otherwise ``is_valid=False`` plus a human-readable ``reason``.
    """
    tz = _get_timezone()
    now = datetime.now(tz)
    effective_now = now + timedelta(minutes=buffer_minutes)

    # Ensure timezone-aware comparison
    if requested_dt.tzinfo is None:
        requested_dt = requested_dt.replace(tzinfo=tz)

    # ---- past-time check ----
    if requested_dt < effective_now:
        logger.warning(
            "past_time_blocked",
            requested=requested_dt.isoformat(),
            effective_now=effective_now.isoformat(),
        )
        return ValidationResult(
            is_valid=False,
            reason=f"Requested time {requested_dt.strftime('%Y-%m-%d %H:%M')} is in the past",
        )

    # ---- weekend check ----
    if requested_dt.weekday() >= 5:
        return ValidationResult(
            is_valid=False,
            reason="Requested time falls on a weekend",
        )

    # ---- business-hours check ----
    bh_start, bh_end = _business_hours()
    duration_mins = getattr(settings, "appointment_duration_minutes", 60)
    slot_end_time = (requested_dt + timedelta(minutes=duration_mins)).time()

    if requested_dt.time() < bh_start or slot_end_time > bh_end:
        return ValidationResult(
            is_valid=False,
            reason=(
                f"Requested time is outside business hours "
                f"({settings.business_hours_start}–{settings.business_hours_end})"
            ),
        )

    logger.info(
        "requested_time_valid",
        requested=requested_dt.isoformat(),
    )
    return ValidationResult(is_valid=True)


def enforce_future_time(
    requested_dt: datetime,
    buffer_minutes: int = FUTURE_BUFFER_MINUTES,
) -> datetime:
    """
    Return ``requested_dt`` if it is in the future (beyond the buffer),
    otherwise return ``now + buffer_minutes`` in the business timezone.

    This is a *floor* function: it never returns a time earlier than
    ``now + buffer``.
    """
    tz = _get_timezone()
    now = datetime.now(tz)
    effective_now = now + timedelta(minutes=buffer_minutes)

    if requested_dt.tzinfo is None:
        requested_dt = requested_dt.replace(tzinfo=tz)

    if requested_dt < effective_now:
        logger.info(
            "past_time_corrected",
            original=requested_dt.isoformat(),
            corrected=effective_now.isoformat(),
        )
        return effective_now

    return requested_dt


def normalize_requested_time(
    requested_dt: datetime,
    round_to_minutes: int = 15,
) -> datetime:
    """
    Round *requested_dt* up to the nearest ``round_to_minutes`` boundary.
    E.g. 10:07 → 10:15, 10:00 → 10:00.
    """
    minute = requested_dt.minute
    remainder = minute % round_to_minutes
    if remainder == 0:
        return requested_dt.replace(second=0, microsecond=0)
    add = round_to_minutes - remainder
    return (requested_dt + timedelta(minutes=add)).replace(second=0, microsecond=0)
