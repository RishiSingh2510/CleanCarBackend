"""Request/response models. JSON uses camelCase to match the mobile app's TypeScript types."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---- requests (length caps stop absurd payloads; precise rules live in app/domain/validation.py) ----
class RegisterIn(CamelModel):
    name: str = Field(max_length=200)
    identifier: str = Field(max_length=300)
    password: str = Field(max_length=300)


class LoginIn(CamelModel):
    identifier: str = Field(max_length=300)
    password: str = Field(max_length=300)


class ForgotPasswordIn(CamelModel):
    identifier: str = Field(max_length=300)


class ResetPasswordIn(CamelModel):
    token: str = Field(max_length=300)
    password: str = Field(max_length=300)


class ProfileUpdateIn(CamelModel):
    name: str = Field(max_length=200)


class VehicleIn(CamelModel):
    brand: str = Field(max_length=200)
    model: str = Field(max_length=200)
    number: str = Field(max_length=100)
    fuel: str = Field(default="", max_length=200)
    type: str = Field(default="", max_length=200)


class VehiclePatchIn(CamelModel):
    brand: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    number: str | None = Field(default=None, max_length=100)
    fuel: str | None = Field(default=None, max_length=200)
    type: str | None = Field(default=None, max_length=200)


class AddressIn(CamelModel):
    label: str = Field(default="Home", max_length=20)
    line1: str = Field(max_length=300)
    line2: str = Field(max_length=300)


class BookingIn(CamelModel):
    service_id: str = Field(max_length=20)
    vehicle_id: str = Field(max_length=64)
    date: str = Field(max_length=20, description="YYYY-MM-DD (India time)")
    time: str = Field(
        max_length=20, description='A slot from GET /slots, e.g. "11:00 AM"'
    )
    address: AddressIn
    payment_method: str = Field(max_length=10, description="upi | card | cod")
    payment_ref: str | None = Field(default=None, max_length=200)
    coupon_code: str | None = Field(default=None, max_length=50)


class RescheduleIn(CamelModel):
    date: str = Field(max_length=20)
    time: str = Field(max_length=20)


class RatingIn(CamelModel):
    rating: StrictInt


class QuoteIn(CamelModel):
    service_id: str = Field(max_length=20)
    coupon_code: str | None = Field(default=None, max_length=50)


class CouponValidateIn(CamelModel):
    code: str = Field(max_length=50)
    service_id: str = Field(max_length=20)


# ---- responses ----
class UserOut(CamelModel):
    name: str
    identifier: str


class AuthOut(CamelModel):
    token: str
    user: UserOut
    expires_at: str


class ServiceOut(CamelModel):
    id: str
    title: str
    desc: str
    price: int
    duration_minutes: int


class CouponOut(CamelModel):
    code: str
    title: str
    desc: str
    type: Literal["percent", "flat"]
    value: int
    max_discount: int | None = None
    min_order: int


class QuoteOut(CamelModel):
    service_id: str
    service_title: str
    subtotal: int
    discount: int
    taxes: int
    total: int
    coupon_code: str | None = None


class VehicleOut(CamelModel):
    id: str
    brand: str
    model: str
    number: str
    fuel: str
    type: str


class SlotOut(CamelModel):
    time: str
    available: bool
    remaining: int


class SlotsOut(CamelModel):
    date: str
    slots: list[SlotOut]


class BookingOut(CamelModel):
    id: str
    service_id: str
    service_title: str
    vehicle_id: str
    vehicle_name: str
    vehicle_number: str
    vehicle_type: str
    date: str
    date_iso: str = Field(alias="dateISO")
    time: str
    address_label: str
    address_text: str
    subtotal: int
    discount: int
    taxes: int
    total: int
    coupon_code: str | None = None
    payment_method: str
    payment_ref: str | None = None
    payment_status: str
    status: Literal["Confirmed", "Cancelled"]
    display_status: Literal["Upcoming", "Completed", "Cancelled"]
    created_at: str
    rating: int | None = None
