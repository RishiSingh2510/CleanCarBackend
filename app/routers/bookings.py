from fastapi import APIRouter, Depends, Query

from app.deps import get_store, get_user
from app.schemas import BookingIn, BookingOut, RatingIn, RescheduleIn
from app.serializers import booking_out
from app.services import booking_service
from app.store import Store, User

router = APIRouter(prefix="/bookings", tags=["bookings"])

# exclude_none: optional fields (couponCode, paymentRef, rating) are simply omitted when empty


@router.get("", response_model=list[BookingOut], response_model_exclude_none=True)
def list_bookings(
    status: str | None = Query(
        default=None, description="Upcoming | Completed | Cancelled"
    ),
    user: User = Depends(get_user),
    store: Store = Depends(get_store),
):
    now = store.now()
    return [
        booking_out(b, now) for b in booking_service.list_bookings(store, user, status)
    ]


@router.post(
    "", response_model=BookingOut, response_model_exclude_none=True, status_code=201
)
def create_booking(
    body: BookingIn, user: User = Depends(get_user), store: Store = Depends(get_store)
):
    booking = booking_service.create_booking(
        store,
        user,
        service_id=body.service_id,
        vehicle_id=body.vehicle_id,
        date=body.date,
        time=body.time,
        address=body.address.model_dump(),
        payment_method=body.payment_method,
        payment_ref=body.payment_ref,
        coupon_code=body.coupon_code,
    )
    return booking_out(booking, store.now())


@router.get(
    "/{booking_id}", response_model=BookingOut, response_model_exclude_none=True
)
def get_booking(
    booking_id: str, user: User = Depends(get_user), store: Store = Depends(get_store)
):
    return booking_out(
        booking_service.get_booking(store, user, booking_id), store.now()
    )


@router.post(
    "/{booking_id}/cancel", response_model=BookingOut, response_model_exclude_none=True
)
def cancel_booking(
    booking_id: str, user: User = Depends(get_user), store: Store = Depends(get_store)
):
    return booking_out(
        booking_service.cancel_booking(store, user, booking_id), store.now()
    )


@router.post(
    "/{booking_id}/reschedule",
    response_model=BookingOut,
    response_model_exclude_none=True,
)
def reschedule_booking(
    booking_id: str,
    body: RescheduleIn,
    user: User = Depends(get_user),
    store: Store = Depends(get_store),
):
    return booking_out(
        booking_service.reschedule_booking(
            store, user, booking_id, body.date, body.time
        ),
        store.now(),
    )


@router.post(
    "/{booking_id}/rating", response_model=BookingOut, response_model_exclude_none=True
)
def rate_booking(
    booking_id: str,
    body: RatingIn,
    user: User = Depends(get_user),
    store: Store = Depends(get_store),
):
    return booking_out(
        booking_service.rate_booking(store, user, booking_id, body.rating), store.now()
    )
