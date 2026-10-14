from dataclasses import dataclass
from typing import Literal

from app.errors import AppError


@dataclass(frozen=True)
class Service:
    id: str
    title: str
    description: str
    price: int  # rupees
    duration_minutes: int


TIME_SLOTS: tuple[str, ...] = (
    "09:00 AM",
    "10:00 AM",
    "11:00 AM",
    "12:00 PM",
    "01:00 PM",
    "02:00 PM",
    "03:00 PM",
    "04:00 PM",
    "05:00 PM",
)

TAXES_AND_FEES = 80  # flat, rupees

PAYMENT_METHODS = ("upi", "card", "cod")
ADDRESS_LABELS = ("Home", "Work", "Other")


@dataclass(frozen=True)
class Coupon:
    code: str
    title: str
    desc: str
    type: Literal["percent", "flat"]
    value: int
    max_discount: int | None
    min_order: int


def find_coupon(code: str) -> Coupon | None:
    c = code.strip().upper()
    return next((x for x in [] if x.code == c), None)
