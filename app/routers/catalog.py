from app.domain.catalog import COUPONS, SERVICES
from app.domain.pricing import build_quote
from fastapi import APIRouter, Depends, Query

from app.deps import get_store
from app.schemas import (
    CouponOut,
    CouponValidateIn,
    QuoteIn,
    QuoteOut,
    ServiceOut,
    SlotsOut,
)
from app.serializers import coupon_out, quote_out, service_out
from app.services import booking_service
from app.store import Store

router = APIRouter(tags=["catalog"])


@router.get("/services", response_model=list[ServiceOut])
def list_services():
    return [service_out(s) for s in SERVICES]


@router.get("/coupons", response_model=list[CouponOut])
def list_coupons():
    return [coupon_out(c) for c in COUPONS]


@router.post("/quote", response_model=QuoteOut)
def quote(body: QuoteIn):
    """Server-calculated price (optionally with a coupon). Show this to the user instead of computing it locally."""
    return quote_out(build_quote(body.service_id, body.coupon_code))


@router.post("/coupons/validate", response_model=QuoteOut)
def validate_coupon(body: CouponValidateIn):
    return quote_out(build_quote(body.service_id, body.code))


@router.get("/slots", response_model=SlotsOut)
def slots(
    date: str = Query(description="YYYY-MM-DD (India time)"),
    store: Store = Depends(get_store),
):
    day = date.strip()
    return {"date": day, "slots": booking_service.slot_availability(store, day)}
