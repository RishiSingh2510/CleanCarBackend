"""Turns store objects into the camelCase dicts the response models expect."""

from datetime import date, datetime
from typing import Any

from app.domain.catalog import Coupon, Service
from app.domain.pricing import Quote
from app.domain.scheduling import scheduled_at
from app.services.auth_service import AuthResult
from app.services.booking_service import status_of
from app.store import Booking, User, Vehicle


def user_out(u: User) -> dict[str, Any]:
    return {"name": u.name, "identifier": u.identifier}


def auth_out(r: AuthResult) -> dict[str, Any]:
    return {
        "token": r.token,
        "user": user_out(r.user),
        "expiresAt": r.expires_at.isoformat(),
    }


def service_out(s: Service) -> dict[str, Any]:
    return {
        "id": s.id,
        "title": s.title,
        "desc": s.desc,
        "price": s.price,
        "durationMinutes": s.duration_minutes,
    }


def coupon_out(c: Coupon) -> dict[str, Any]:
    return {
        "code": c.code,
        "title": c.title,
        "desc": c.desc,
        "type": c.type,
        "value": c.value,
        "maxDiscount": c.max_discount,
        "minOrder": c.min_order,
    }


def quote_out(q: Quote) -> dict[str, Any]:
    return {
        "serviceId": q.service.id,
        "serviceTitle": q.service.title,
        "subtotal": q.subtotal,
        "discount": q.discount,
        "taxes": q.taxes,
        "total": q.total,
        "couponCode": q.coupon_code,
    }


def vehicle_out(v: Vehicle) -> dict[str, Any]:
    return {
        "id": v.id,
        "brand": v.brand,
        "model": v.model,
        "number": v.number,
        "fuel": v.fuel,
        "type": v.type,
    }


def booking_out(b: Booking, now: datetime) -> dict[str, Any]:
    return {
        "id": b.id,
        "serviceId": b.service_id,
        "serviceTitle": b.service_title,
        "vehicleId": b.vehicle_id,
        "vehicleName": b.vehicle_name,
        "vehicleNumber": b.vehicle_number,
        "vehicleType": b.vehicle_type,
        "date": b.date,
        "dateISO": scheduled_at(
            date.fromisoformat(b.date), b.time
        ).isoformat(),  # appointment instant, +05:30
        "time": b.time,
        "addressLabel": b.address_label,
        "addressText": b.address_text,
        "subtotal": b.subtotal,
        "discount": b.discount,
        "taxes": b.taxes,
        "total": b.total,
        "couponCode": b.coupon_code,
        "paymentMethod": b.payment_method,
        "paymentRef": b.payment_ref,
        "paymentStatus": b.payment_status,
        "status": b.status,
        "displayStatus": status_of(b, now),
        "createdAt": b.created_at.isoformat(),
        "rating": b.rating,
    }
