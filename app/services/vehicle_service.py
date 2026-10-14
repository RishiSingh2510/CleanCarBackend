import re
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row

from app.config import get_settings
from app.domain.validation import clean_text
from app.errors import AppError
from app.store import User, Vehicle, new_id

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


def _vehicle(row: dict[str, Any]) -> Vehicle:
    return Vehicle(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        brand=row["brand"],
        model=row["model"],
        number=row["number"],
        fuel=row["fuel"],
        type=row["type"],
    )


def list_vehicles(conn: Connection, user: User) -> list[Vehicle]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, user_id, brand, model, number, fuel, type
            FROM public."Vehicles"
            WHERE user_id = %s
            ORDER BY id
            """,
            (user.id,),
        )
        rows = cur.fetchall()
    return [_vehicle(row) for row in rows]


def get_owned_vehicle(conn: Connection, user: User, vehicle_id: str) -> Vehicle:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, user_id, brand, model, number, fuel, type
            FROM public."Vehicles"
            WHERE id = %s AND user_id = %s
            """,
            (vehicle_id, user.id),
        )
        row = cur.fetchone()
    if row is None:  # 404, not 403: don't reveal other people's ids
        raise AppError(404, "VEHICLE_NOT_FOUND", "We couldn't find that vehicle.")
    return _vehicle(row)


def create_vehicle(conn: Connection, user: User, data: dict[str, Any]) -> Vehicle:
    fields = _clean(data)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            'SELECT COUNT(*) AS count FROM public."Vehicles" WHERE user_id = %s',
            (user.id,),
        )
        count = cur.fetchone()["count"]
        if count >= get_settings().max_vehicles_per_user:
            raise AppError(
                409,
                "VEHICLE_LIMIT",
                f"You can save up to {get_settings().max_vehicles_per_user} cars.",
            )
        cur.execute(
            """
            SELECT EXISTS(
                SELECT 1 FROM public."Vehicles"
                WHERE user_id = %s AND number = %s
            ) AS is_duplicate
            """,
            (user.id, fields["number"]),
        )
        if cur.fetchone()["is_duplicate"]:
            raise AppError(
                409, "VEHICLE_EXISTS", "You have already saved a car with this number."
            )
        cur.execute(
            """
            INSERT INTO public."Vehicles" (id, user_id, brand, model, number, fuel, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, brand, model, number, fuel, type
            """,
            (
                new_id(),
                user.id,
                fields["brand"],
                fields["model"],
                fields["number"],
                fields["fuel"],
                fields["type"],
            ),
        )
        row = cur.fetchone()
    return _vehicle(row)


def update_vehicle(
    conn: Connection, user: User, vehicle_id: str, patch: dict[str, Any]
) -> Vehicle:
    vehicle = get_owned_vehicle(conn, user, vehicle_id)
    merged = {
        "brand": vehicle.brand,
        "model": vehicle.model,
        "number": vehicle.number,
        "fuel": vehicle.fuel,
        "type": vehicle.type,
        **{key: value for key, value in patch.items() if value is not None},
    }
    fields = _clean(merged)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT EXISTS(
                SELECT 1 FROM public."Vehicles"
                WHERE user_id = %s AND number = %s AND id <> %s
            ) AS is_duplicate
            """,
            (user.id, fields["number"], vehicle.id),
        )
        if cur.fetchone()["is_duplicate"]:
            raise AppError(
                409, "VEHICLE_EXISTS", "You have already saved a car with this number."
            )
        cur.execute(
            """
            UPDATE public."Vehicles"
            SET brand = %s, model = %s, number = %s, fuel = %s, type = %s
            WHERE id = %s AND user_id = %s
            RETURNING id, user_id, brand, model, number, fuel, type
            """,
            (
                fields["brand"],
                fields["model"],
                fields["number"],
                fields["fuel"],
                fields["type"],
                vehicle_id,
                user.id,
            ),
        )
        row = cur.fetchone()
    if row is None:
        raise AppError(404, "VEHICLE_NOT_FOUND", "We couldn't find that vehicle.")
    return _vehicle(row)


def delete_vehicle(conn: Connection, user: User, vehicle_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM public."Vehicles"
            WHERE id = %s AND user_id = %s
            RETURNING id
            """,
            (vehicle_id, user.id),
        )
        if cur.fetchone() is None:
            raise AppError(404, "VEHICLE_NOT_FOUND", "We couldn't find that vehicle.")
