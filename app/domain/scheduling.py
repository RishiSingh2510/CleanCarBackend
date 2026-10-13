import re
from datetime import date, datetime, time, timedelta, timezone

from app.errors import AppError

# India has no daylight saving, so a fixed offset is exact (and avoids needing tz databases on Windows).
IST = timezone(timedelta(hours=5, minutes=30))

_SLOT = re.compile(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", re.IGNORECASE)


def parse_slot(slot: str) -> time:
    m = _SLOT.match(slot.strip())
    if not m:
        raise AppError(
            422, "VALIDATION_ERROR", "Choose one of the available time slots."
        )
    hour = int(m.group(1)) % 12
    if m.group(3).upper() == "PM":
        hour += 12
    return time(hour, int(m.group(2)))


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        raise AppError(
            422, "VALIDATION_ERROR", "Date must be in YYYY-MM-DD format."
        ) from None


def scheduled_at(day: date, slot: str) -> datetime:
    return datetime.combine(day, parse_slot(slot), tzinfo=IST)


def display_status(status: str, date_str: str, slot: str, now: datetime) -> str:
    """'Upcoming' | 'Completed' | 'Cancelled' — same rules as the mobile app."""
    if status == "Cancelled":
        return "Cancelled"
    return (
        "Upcoming"
        if scheduled_at(date.fromisoformat(date_str), slot) > now
        else "Completed"
    )
