import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from app.domain.scheduling import IST

from app.config import Settings, get_settings


def new_id() -> str:
    return uuid.uuid4().hex


@dataclass
class User:
    id: str
    name: str
    identifier: str  # normalized email or +91 phone
    password_hash: str
    created_at: datetime


@dataclass
class Session:
    user_id: str
    expires_at: datetime


@dataclass
class ResetToken:
    user_id: str
    expires_at: datetime


@dataclass
class Vehicle:
    id: str
    user_id: str
    brand: str
    model: str
    number: str
    fuel: str
    type: str


@dataclass
class Booking:
    id: str
    user_id: str
    service_id: str
    service_title: str
    vehicle_id: str
    vehicle_name: str
    vehicle_number: str
    vehicle_type: str
    date: str  # YYYY-MM-DD (India time)
    time: str  # "11:00 AM"
    address_label: str
    address_text: str
    subtotal: int
    discount: int
    taxes: int
    total: int
    coupon_code: str | None
    payment_method: str
    payment_ref: str | None
    payment_status: str  # paid | pending | refund_pending
    status: str  # Confirmed | Cancelled
    created_at: datetime
    cancelled_at: datetime | None = None
    rating: int | None = None


@dataclass
class Store:
    """
    The whole "database": plain dicts guarded by one lock. Data disappears when the process stops and is NOT shared
    between processes — run a single uvicorn worker. Swap this class for a real DB layer when you outgrow it.
    """

    settings: Settings = field(default_factory=get_settings)
    clock: Callable[[], datetime] = field(default=lambda: datetime.now(IST))
    lock: threading.RLock = field(default_factory=threading.RLock)

    users: dict[str, User] = field(default_factory=dict)
    user_ids_by_identifier: dict[str, str] = field(default_factory=dict)
    sessions: dict[str, Session] = field(default_factory=dict)  # key = sha256(token)
    reset_tokens: dict[str, ResetToken] = field(
        default_factory=dict
    )  # key = sha256(token)
    vehicles: dict[str, Vehicle] = field(default_factory=dict)
    bookings: dict[str, Booking] = field(default_factory=dict)
    login_failures: dict[str, list[datetime]] = field(default_factory=dict)

    def now(self) -> datetime:
        return self.clock()

    def user_by_identifier(self, identifier: str) -> User | None:
        uid = self.user_ids_by_identifier.get(identifier)
        return self.users.get(uid) if uid else None
