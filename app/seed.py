import logging

from psycopg import Connection
from psycopg.rows import dict_row

from app.services import auth_service, vehicle_service
from app.store import Store

log = logging.getLogger("cleancar")

DEMO_IDENTIFIER = "demo@cleancar.in"
DEMO_PASSWORD = "demo1234"


def seed_demo(store: Store, conn: Connection) -> None:
    """Creates a demo account so you can log in right after starting the server (development only)."""
    if store.settings.is_production:
        raise RuntimeError("SEED_DEMO must not be enabled when APP_ENV=production")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            'SELECT id FROM public."Users" WHERE identifier = %s',
            (DEMO_IDENTIFIER,),
        )
        if cur.fetchone():
            return
    res = auth_service.register(
        conn, store, "Demo User", DEMO_IDENTIFIER, DEMO_PASSWORD
    )
    vehicle_service.create_vehicle(
        conn,
        res.user,
        {
            "brand": "Toyota",
            "model": "Fortuner",
            "number": "MH12AB1234",
            "fuel": "Diesel",
            "type": "SUV",
        },
    )
    log.warning(
        "Demo data seeded — login: %s / %s (development only)",
        DEMO_IDENTIFIER,
        DEMO_PASSWORD,
    )
