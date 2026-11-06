"""
Tests for the scheduling validation layer.
Covers: past-time blocking, business hours, weekends, enforce_future_time, normalize.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.services.scheduling.validation import (
    validate_requested_time,
    enforce_future_time,
    normalize_requested_time,
    FUTURE_BUFFER_MINUTES,
)

TZ = ZoneInfo("America/New_York")


def _next_weekday(dt: datetime) -> datetime:
    """Advance dt until it lands on a weekday."""
    while dt.weekday() >= 5:
        dt += timedelta(days=1)
    return dt


def _next_saturday(dt: datetime) -> datetime:
    """Advance dt until it lands on a Saturday."""
    while dt.weekday() != 5:
        dt += timedelta(days=1)
    return dt


class TestValidateRequestedTime:

    def test_past_time_rejected(self):
        past = datetime.now(TZ) - timedelta(hours=2)
        r = validate_requested_time(past)
        assert not r.is_valid
        assert "past" in r.reason.lower()

    def test_valid_future_accepted(self):
        future = _next_weekday(
            datetime.now(TZ).replace(hour=10, minute=0, second=0, microsecond=0)
            + timedelta(days=1)
        )
        r = validate_requested_time(future)
        assert r.is_valid

    def test_weekend_rejected(self):
        sat = _next_saturday(datetime.now(TZ))
        sat = sat.replace(hour=10, minute=0, second=0, microsecond=0)
        r = validate_requested_time(sat)
        assert not r.is_valid
        assert "weekend" in r.reason.lower()

    def test_after_hours_rejected(self):
        future = _next_weekday(
            datetime.now(TZ).replace(hour=19, minute=0, second=0, microsecond=0)
            + timedelta(days=1)
        )
        r = validate_requested_time(future)
        assert not r.is_valid
        assert "business hours" in r.reason.lower()

    def test_before_hours_rejected(self):
        future = _next_weekday(
            datetime.now(TZ).replace(hour=6, minute=0, second=0, microsecond=0)
            + timedelta(days=1)
        )
        r = validate_requested_time(future)
        assert not r.is_valid
        assert "business hours" in r.reason.lower()


class TestEnforceFutureTime:

    def test_past_corrected_to_future(self):
        past = datetime.now(TZ) - timedelta(hours=1)
        corrected = enforce_future_time(past)
        assert corrected > datetime.now(TZ)

    def test_future_unchanged(self):
        future = datetime.now(TZ) + timedelta(hours=3)
        result = enforce_future_time(future)
        assert result == future

    def test_within_buffer_corrected(self):
        """A time only 5 min from now should be pushed past the buffer."""
        near = datetime.now(TZ) + timedelta(minutes=5)
        corrected = enforce_future_time(near, buffer_minutes=FUTURE_BUFFER_MINUTES)
        assert corrected > near


class TestNormalizeRequestedTime:

    def test_round_up(self):
        t = datetime(2026, 5, 6, 10, 7, 23, tzinfo=TZ)
        n = normalize_requested_time(t)
        assert n.minute == 15
        assert n.second == 0

    def test_already_aligned(self):
        t = datetime(2026, 5, 6, 10, 0, 0, tzinfo=TZ)
        n = normalize_requested_time(t)
        assert n.minute == 0

    def test_round_up_45(self):
        t = datetime(2026, 5, 6, 10, 46, 0, tzinfo=TZ)
        n = normalize_requested_time(t)
        assert n.hour == 11
        assert n.minute == 0
