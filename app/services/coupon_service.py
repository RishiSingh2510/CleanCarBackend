from psycopg import Connection
from psycopg.rows import dict_row


def get_coupons(conn: Connection):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT code,
            title,
            description AS desc,
            type,
            value,
            max_discount,
            min_order
            FROM public."Coupons"
            ORDER BY value
        """
        )
        rows = cur.fetchall()

    return rows


def get_coupon_by_code(conn: Connection, coupon_code: str):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT code,
            title,
            description AS desc,
            type,
            value,
            max_discount,
            min_order
            FROM public."Coupons"
            WHERE code = %s
         """,
            (coupon_code,),
        )
        rows = cur.fetchall()

    return rows[0]
