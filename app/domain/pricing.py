from dataclasses import dataclass

from psycopg import Connection

from app.domain.catalog import TAXES_AND_FEES, Coupon, Service
from app.errors import AppError
from app.services import car_services_service, coupon_service


@dataclass(frozen=True)
class Quote:
    service: Service
    subtotal: int
    discount: int
    taxes: int
    total: int
    coupon_code: str | None


def discount_for(coupon: Coupon, subtotal: int) -> int:
    if subtotal < coupon.min_order:
        return 0
    raw = (
        coupon.value if coupon.type == "flat" else (subtotal * coupon.value + 50) // 100
    )  # round half up
    capped = min(raw, coupon.max_discount) if coupon.max_discount else raw
    return min(capped, subtotal)


def build_quote(
    conn: Connection, service_id: str, coupon_code: str | None = None
) -> Quote:
    """The single source of truth for prices — the client's numbers are never trusted."""

    service = car_services_service.get_service(conn, service_id)
    subtotal = service.get("price")
    discount = 0
    applied: str | None = None

    if coupon_code and coupon_code.strip():
        coupon = coupon_service.get_coupon_by_code(conn, coupon_code)
        if coupon is None:
            raise AppError(422, "COUPON_INVALID", "This coupon code is not valid.")
        if subtotal < coupon.get("min_order"):
            raise AppError(
                422,
                "COUPON_MIN_ORDER",
                f"Add services worth ₹{coupon.get('min_order') - subtotal} more to use {coupon.get('code')}.",
            )
        discount = discount_for(coupon, subtotal)
        applied = coupon.get("code")

    return Quote(
        service,
        subtotal,
        discount,
        TAXES_AND_FEES,
        subtotal - discount + TAXES_AND_FEES,
        applied,
    )
