from app.errors import AppError
from app.database import get_db
from app.services import auth_service
from app.services.auth_service import Principal
from app.store import Store, User
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import Connection

_store = Store()  # the one in-memory database for this process
_bearer = HTTPBearer(auto_error=False)


def get_store() -> Store:
    return _store


def get_principal(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    store: Store = Depends(get_store),
    conn: Connection = Depends(get_db),
) -> Principal:
    if creds is None or not creds.credentials:
        raise AppError(
            401,
            "UNAUTHORIZED",
            "Please sign in to continue.",
            {"WWW-Authenticate": "Bearer"},
        )
    return auth_service.authenticate(conn, store, creds.credentials)


def get_user(principal: Principal = Depends(get_principal)) -> User:
    return principal.user
