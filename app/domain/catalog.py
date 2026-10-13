from dataclasses import dataclass
from typing import Literal

from app.errors import AppError


@dataclass(frozen=True)
class Service:
    id: str
    title: str
    desc: str
    price: int  # rupees
    duration_minutes: int


SERVICES: tuple[Service, ...] = (
    Service("1", "Basic Wash", "Exterior wash & cleaning", 299, 30),
    Service("2", "Premium Wash", "Exterior + interior cleaning", 599, 60),
    Service("3", "Interior Cleaning", "Deep interior cleaning", 799, 90),
    Service("4", "Full Car Detailing", "Complete inside & outside", 1499, 120),
    Service("5", "Ceramic Coating", "Long-lasting protection", 2499, 180),
)

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


COUPONS: tuple[Coupon, ...] = (
    Coupon("FIRST50", "Flat ₹50 off", "On your booking", "flat", 50, None, 0),
    Coupon(
        "WASH20",
        "20% off up to ₹150",
        "On orders of ₹500 or more",
        "percent",
        20,
        150,
        500,
    ),
    Coupon(
        "DETAIL15",
        "15% off up to ₹400",
        "On orders of ₹1,000 or more",
        "percent",
        15,
        400,
        1000,
    ),
)


def get_service(service_id: str) -> Service:
    for s in SERVICES:
        if s.id == service_id:
            return s
    raise AppError(404, "SERVICE_NOT_FOUND", "That service does not exist.")


def find_coupon(code: str) -> Coupon | None:
    c = code.strip().upper()
    return next((x for x in COUPONS if x.code == c), None)
