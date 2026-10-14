from fastapi import APIRouter, Depends
from psycopg import Connection

from app.database import get_db
from app.deps import get_principal, get_store
from app.schemas import AuthOut, ForgotPasswordIn, LoginIn, RegisterIn, ResetPasswordIn
from app.serializers import auth_out
from app.services import auth_service
from app.services.auth_service import Principal
from app.store import Store

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthOut, status_code=201)
def register(
    body: RegisterIn,
    store: Store = Depends(get_store),
    conn: Connection = Depends(get_db),
):
    return auth_out(
        auth_service.register(conn, store, body.name, body.identifier, body.password)
    )


@router.post("/login", response_model=AuthOut)
def login(
    body: LoginIn,
    store: Store = Depends(get_store),
    conn: Connection = Depends(get_db),
):
    return auth_out(auth_service.login(conn, store, body.identifier, body.password))


@router.post("/logout")
def logout(
    principal: Principal = Depends(get_principal), store: Store = Depends(get_store)
):
    auth_service.logout(store, principal)
    return {}


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordIn,
    store: Store = Depends(get_store),
    conn: Connection = Depends(get_db),
):
    auth_service.request_password_reset(conn, store, body.identifier)
    return {}  # always 200, whether or not the account exists


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordIn,
    store: Store = Depends(get_store),
    conn: Connection = Depends(get_db),
):
    auth_service.reset_password(conn, store, body.token, body.password)
    return {}
