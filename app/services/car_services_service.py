from psycopg import Connection
from psycopg.rows import dict_row


def get_all_services(conn: Connection):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id,
            title,
            description,
            price,
            duration_minutes
            FROM public."Services"
            ORDER BY id
        """
        )
        rows = cur.fetchall()

    return rows


def get_service(conn: Connection, service_id: str):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
        SELECT  id,
            title,
            description,
            price,
            duration_minutes
        FROM public."Services"
        WHERE id = %s
        """,
            (service_id,),
        )
        rows = cur.fetchall()

    return rows[0]
