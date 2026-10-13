import re

from app.errors import AppError

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PHONE = re.compile(r"^(\+91)?([6-9]\d{9})$")

MIN_PASSWORD = 6
MAX_PASSWORD = 128


def _bad(message: str) -> AppError:
    return AppError(422, "VALIDATION_ERROR", message)


def normalize_identifier(value: str) -> str:
    """Emails → lower-case. Indian mobiles → canonical +91XXXXXXXXXX (so '98765 43210' == '+91 98765-43210')."""
    t = (value or "").strip()
    if _EMAIL.match(t):
        return t.lower()
    m = _PHONE.match(re.sub(r"[\s-]", "", t))
    return f"+91{m.group(2)}" if m else t


def validate_identifier(value: str) -> str:
    if not (value or "").strip():
        raise _bad("Enter your email or phone number")
    n = normalize_identifier(value)
    if len(n) > 254 or not (_EMAIL.match(n) or _PHONE.match(n)):
        raise _bad("Enter a valid email or 10-digit phone number")
    return n


def validate_password(value: str) -> str:
    if not value:
        raise _bad("Enter your password")
    if len(value) < MIN_PASSWORD:
        raise _bad(f"Password must be at least {MIN_PASSWORD} characters")
    if len(value) > MAX_PASSWORD:
        raise _bad(f"Password must be at most {MAX_PASSWORD} characters")
    return value


def clean_text(
    value: str | None, label: str, min_len: int = 1, max_len: int = 100
) -> str:
    """Trims and collapses whitespace, then enforces a length range."""
    t = re.sub(r"\s+", " ", (value or "").strip())
    if len(t) < min_len or len(t) > max_len:
        if min_len == 0:
            raise _bad(f"{label} must be at most {max_len} characters.")
        raise _bad(f"{label} must be between {min_len} and {max_len} characters.")
    return t


def validate_name(value: str) -> str:
    return clean_text(value, "Name", 1, 60)
