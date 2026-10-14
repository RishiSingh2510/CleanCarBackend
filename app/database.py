import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from dotenv import load_dotenv
from fastapi import HTTPException
from psycopg import Connection

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from .env")

logger = logging.getLogger(__name__)


@contextmanager
def open_db() -> Iterator[Connection]:
    try:
        with psycopg.connect(
            DATABASE_URL,
            connect_timeout=10,
            sslmode="require",
        ) as conn:
            yield conn

    except psycopg.Error:
        logger.exception("Supabase PostgreSQL connection failed")
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Database connection failed",
                "code": "DATABASE_CONNECTION_ERROR",
            },
        )


def get_db():
    with open_db() as conn:
        yield conn
