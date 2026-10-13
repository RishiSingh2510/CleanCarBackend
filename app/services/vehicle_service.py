import re
from typing import Any

from app.domain.validation import clean_text

from app.errors import AppError
from app.store import Store, User, Vehicle, new_id

_NUMBER = re.compile(r"^[A-Z0-9]{4,15}$")


def _clean_number(value: str) -> str:
    n = re.sub(r"[\s-]", "", (value or "").upper())
    if not _NUMBER.match(n):
        raise AppError(
            422, "VALIDATION_ERROR", "Enter a valid car number, e.g. MH12AB1234."
        )
    return n


def _clean(data: dict[str, Any]) -> dict[str, str]:
    return {
        "brand": clean_text(data.get("brand"), "Car brand", 1, 40),
        "model": clean_text(data.get("model"), "Car model", 1, 40),
        "number": _clean_number(data.get("number") or ""),
        "fuel": clean_text(data.get("fuel"), "Fuel type", 0, 20),
        "type": clean_text(data.get("type"), "Car type", 0, 30),
    }


def _mine(store: Store, user: User) -> list[Vehicle]:
    return [v for v in store.vehicles.values() if v.user_id == user.id]


def list_vehicles(store: Store, user: User) -> list[Vehicle]:
    with store.lock:
        return _mine(store, user)


def get_owned_vehicle(store: Store, user: User, vehicle_id: str) -> Vehicle:
    with store.lock:
        v = store.vehicles.get(vehicle_id)
        if (
            v is None or v.user_id != user.id
        ):  # 404, not 403: don't reveal other people's ids
            raise AppError(404, "VEHICLE_NOT_FOUND", "We couldn't find that vehicle.")
        return v


def create_vehicle(store: Store, user: User, data: dict[str, Any]) -> Vehicle:
    fields = _clean(data)
    with store.lock:
        mine = _mine(store, user)
        if len(mine) >= store.settings.max_vehicles_per_user:
            raise AppError(
                409,
                "VEHICLE_LIMIT",
                f"You can save up to {store.settings.max_vehicles_per_user} cars.",
            )
        if any(v.number == fields["number"] for v in mine):
            raise AppError(
                409, "VEHICLE_EXISTS", "You have already saved a car with this number."
            )
        v = Vehicle(id=new_id(), user_id=user.id, **fields)
        store.vehicles[v.id] = v
        return v


def update_vehicle(
    store: Store, user: User, vehicle_id: str, patch: dict[str, Any]
) -> Vehicle:
    with store.lock:
        v = get_owned_vehicle(store, user, vehicle_id)
        merged = {
            "brand": v.brand,
            "model": v.model,
            "number": v.number,
            "fuel": v.fuel,
            "type": v.type,
            **{k: val for k, val in patch.items() if val is not None},
        }
        fields = _clean(merged)
        if any(
            o.number == fields["number"] and o.id != v.id for o in _mine(store, user)
        ):
            raise AppError(
                409, "VEHICLE_EXISTS", "You have already saved a car with this number."
            )
        for k, val in fields.items():
            setattr(v, k, val)
        return v


def delete_vehicle(store: Store, user: User, vehicle_id: str) -> None:
    with store.lock:
        v = get_owned_vehicle(store, user, vehicle_id)
        del store.vehicles[
            v.id
        ]  # existing bookings keep their own copy of the car details
