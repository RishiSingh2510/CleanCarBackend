from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from app.database import get_db
from app.deps import get_store
from app.domain.pricing import build_quote
from app.schemas import (
    CouponOut,
    CouponValidateIn,
    QuoteIn,
    QuoteOut,
    ServiceOut,
    SlotsOut,
)
from app.serializers import coupon_out, quote_out, service_out
from app.services import booking_service, car_services_service, coupon_service
from app.store import Store

router = APIRouter(tags=["catalog"])


@router.get("/services", response_model=list[ServiceOut])
def list_services(conn: Connection = Depends(get_db)):
    services = car_services_service.get_all_services(conn)
    return [service_out(s) for s in services]


@router.get("/coupons", response_model=list[CouponOut])
def list_coupons(conn: Connection = Depends(get_db)):
    coupons = coupon_service.get_coupons(conn)
    return [coupon_out(c) for c in coupons]


@router.post("/quote", response_model=QuoteOut)
def quote(body: QuoteIn, conn: Connection = Depends(get_db)):
    """Server-calculated price (optionally with a coupon). Show this to the user instead of computing it locally."""
    return quote_out(build_quote(conn, body.service_id, body.coupon_code))


@router.post("/coupons/validate", response_model=QuoteOut)
def validate_coupon(body: CouponValidateIn, conn: Connection = Depends(get_db)):
    return quote_out(build_quote(conn, body.service_id, body.code))


@router.get("/slots", response_model=SlotsOut)
def slots(
    date: str = Query(description="YYYY-MM-DD (India time)"),
    store: Store = Depends(get_store),
):
    day = date.strip()
    return {"date": day, "slots": booking_service.slot_availability(store, day)}
