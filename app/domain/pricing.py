from dataclasses import dataclass

from app.domain.catalog import TAXES_AND_FEES, Coupon, Service, find_coupon, get_service
from app.errors import AppError


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


def build_quote(service_id: str, coupon_code: str | None = None) -> Quote:
    """The single source of truth for prices — the client's numbers are never trusted."""
    service = get_service(service_id)
    subtotal = service.price
    discount = 0
    applied: str | None = None

    if coupon_code and coupon_code.strip():
        coupon = find_coupon(coupon_code)
        if coupon is None:
            raise AppError(422, "COUPON_INVALID", "This coupon code is not valid.")
        if subtotal < coupon.min_order:
            raise AppError(
                422,
                "COUPON_MIN_ORDER",
                f"Add services worth ₹{coupon.min_order - subtotal} more to use {coupon.code}.",
            )
        discount = discount_for(coupon, subtotal)
        applied = coupon.code

    return Quote(
        service,
        subtotal,
        discount,
        TAXES_AND_FEES,
        subtotal - discount + TAXES_AND_FEES,
        applied,
    )
