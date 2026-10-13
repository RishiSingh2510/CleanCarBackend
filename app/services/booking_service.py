import secrets
from datetime import datetime, timedelta
from typing import Any

from app.domain.catalog import ADDRESS_LABELS, PAYMENT_METHODS, TIME_SLOTS
from app.domain.pricing import build_quote
from app.domain.scheduling import display_status, parse_date, scheduled_at
from app.domain.validation import clean_text

from app.errors import AppError
from app.services import vehicle_service
from app.store import Booking, Store, User

STATUS_FILTERS = ("Upcoming", "Completed", "Cancelled")


def status_of(b: Booking, now: datetime) -> str:
    return display_status(b.status, b.date, b.time, now)


def _new_booking_id(store: Store) -> str:
    while True:
        bid = f"CW{100000 + secrets.randbelow(900000)}"
        if bid not in store.bookings:
            return bid


def _clean_address(addr: dict[str, Any]) -> tuple[str, str]:
    label = (addr.get("label") or "Home").strip().title()
    if label not in ADDRESS_LABELS:
        raise AppError(
            422, "VALIDATION_ERROR", "Address label must be Home, Work or Other."
        )
    line1 = clean_text(addr.get("line1"), "Address line 1", 3, 120)
    line2 = clean_text(addr.get("line2"), "Address line 2", 3, 120)
    return label, f"{line1}, {line2}"


def _active_at(
    store: Store, date_str: str, slot: str, exclude_id: str | None = None
) -> list[Booking]:
    return [
        b
        for b in store.bookings.values()
        if b.status == "Confirmed"
        and b.date == date_str
        and b.time == slot
        and b.id != exclude_id
    ]


def _check_slot(
    store: Store,
    date_str: str,
    slot: str,
    now: datetime,
    *,
    vehicle_id: str,
    exclude_id: str | None = None,
) -> datetime:
    """Validates a date + slot for booking/rescheduling. Returns the appointment time."""
    day = parse_date(date_str)
    if slot not in TIME_SLOTS:
        raise AppError(
            422, "VALIDATION_ERROR", "Choose one of the available time slots."
        )
    when = scheduled_at(day, slot)
    if when <= now + timedelta(minutes=store.settings.min_lead_minutes):
        raise AppError(
            422,
            "SLOT_IN_PAST",
            "That time slot has already passed. Please pick a later one.",
        )
    if day > now.date() + timedelta(days=store.settings.booking_window_days):
        raise AppError(
            422,
            "DATE_TOO_FAR",
            f"You can book up to {store.settings.booking_window_days} days ahead.",
        )
    taken = _active_at(store, date_str, slot, exclude_id)
    if len(taken) >= store.settings.slot_capacity:
        raise AppError(
            409, "SLOT_FULL", "That time slot is fully booked. Please choose another."
        )
    if any(b.vehicle_id == vehicle_id for b in taken):
        raise AppError(
            409, "DUPLICATE_BOOKING", "This car already has a booking at that time."
        )
    return when


def slot_availability(store: Store, date_str: str) -> list[dict[str, Any]]:
    day = parse_date(date_str)
    with store.lock:
        now = store.now()
        out = []
        for slot in TIME_SLOTS:
            past = scheduled_at(day, slot) <= now + timedelta(
                minutes=store.settings.min_lead_minutes
            )
            remaining = max(
                0,
                store.settings.slot_capacity
                - len(_active_at(store, day.isoformat(), slot)),
            )
            out.append(
                {
                    "time": slot,
                    "available": (not past) and remaining > 0,
                    "remaining": 0 if past else remaining,
                }
            )
        return out


def create_booking(
    store: Store,
    user: User,
    *,
    service_id: str,
    vehicle_id: str,
    date: str,
    time: str,
    address: dict[str, Any],
    payment_method: str,
    payment_ref: str | None,
    coupon_code: str | None,
) -> Booking:
    quote = build_quote(
        service_id, coupon_code
    )  # prices come from the server, never the client
    label, address_text = _clean_address(address)
    if payment_method not in PAYMENT_METHODS:
        raise AppError(422, "VALIDATION_ERROR", "Choose a valid payment method.")
    ref = (payment_ref or "").strip()[:100] or None
    if payment_method != "cod" and ref is None:
        raise AppError(
            422,
            "PAYMENT_REQUIRED",
            "A payment reference is required for online payments.",
        )

    with store.lock:
        vehicle = vehicle_service.get_owned_vehicle(store, user, vehicle_id)
        now = store.now()
        _check_slot(store, date, time, now, vehicle_id=vehicle.id)
        booking = Booking(
            id=_new_booking_id(store),
            user_id=user.id,
            service_id=quote.service.id,
            service_title=quote.service.title,
            vehicle_id=vehicle.id,
            vehicle_name=f"{vehicle.brand} {vehicle.model}",
            vehicle_number=vehicle.number,
            vehicle_type=vehicle.type,
            date=parse_date(date).isoformat(),
            time=time,
            address_label=label,
            address_text=address_text,
            subtotal=quote.subtotal,
            discount=quote.discount,
            taxes=quote.taxes,
            total=quote.total,
            coupon_code=quote.coupon_code,
            payment_method=payment_method,
            payment_ref=ref,
            # TODO(production): verify `payment_ref` with your payment gateway before marking it paid.
            payment_status="pending" if payment_method == "cod" else "paid",
            status="Confirmed",
            created_at=now,
        )
        store.bookings[booking.id] = booking
        return booking


def _owned(store: Store, user: User, booking_id: str) -> Booking:
    b = store.bookings.get(booking_id)
    if (
        b is None or b.user_id != user.id
    ):  # 404, not 403: don't reveal other people's ids
        raise AppError(404, "BOOKING_NOT_FOUND", "We couldn't find that booking.")
    return b


def get_booking(store: Store, user: User, booking_id: str) -> Booking:
    with store.lock:
        return _owned(store, user, booking_id)


def list_bookings(store: Store, user: User, status: str | None = None) -> list[Booking]:
    if status is not None and status not in STATUS_FILTERS:
        raise AppError(
            422, "VALIDATION_ERROR", "Status must be Upcoming, Completed or Cancelled."
        )
    with store.lock:
        now = store.now()
        mine = [b for b in store.bookings.values() if b.user_id == user.id]
        if status:
            mine = [b for b in mine if status_of(b, now) == status]
        key = lambda b: scheduled_at(parse_date(b.date), b.time)  # noqa: E731
        return sorted(
            mine, key=key, reverse=(status != "Upcoming")
        )  # soonest first for Upcoming, newest first otherwise


def cancel_booking(store: Store, user: User, booking_id: str) -> Booking:
    with store.lock:
        b = _owned(store, user, booking_id)
        current = status_of(b, store.now())
        if current == "Cancelled":
            raise AppError(
                409, "ALREADY_CANCELLED", "This booking is already cancelled."
            )
        if current != "Upcoming":
            raise AppError(
                409, "CANNOT_CANCEL", "Only upcoming bookings can be cancelled."
            )
        b.status = "Cancelled"
        b.cancelled_at = store.now()
        if b.payment_status == "paid":
            b.payment_status = "refund_pending"  # TODO(production): trigger the refund with your gateway
        return b


def reschedule_booking(
    store: Store, user: User, booking_id: str, date: str, time: str
) -> Booking:
    with store.lock:
        b = _owned(store, user, booking_id)
        now = store.now()
        if status_of(b, now) != "Upcoming":
            raise AppError(
                409, "CANNOT_RESCHEDULE", "Only upcoming bookings can be rescheduled."
            )
        _check_slot(store, date, time, now, vehicle_id=b.vehicle_id, exclude_id=b.id)
        b.date = parse_date(date).isoformat()
        b.time = time
        return b


def rate_booking(store: Store, user: User, booking_id: str, rating: int) -> Booking:
    if not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 5:
        raise AppError(
            422, "VALIDATION_ERROR", "Rating must be a whole number from 1 to 5."
        )
    with store.lock:
        b = _owned(store, user, booking_id)
        if status_of(b, store.now()) != "Completed":
            raise AppError(
                409,
                "NOT_COMPLETED",
                "You can rate a booking once the service is completed.",
            )
        b.rating = rating
        return b
