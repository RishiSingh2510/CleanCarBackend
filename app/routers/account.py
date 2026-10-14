from fastapi import APIRouter, Depends
from psycopg import Connection

from app.database import get_db
from app.deps import get_store, get_user
from app.schemas import ProfileUpdateIn, UserOut
from app.serializers import user_out
from app.services import auth_service
from app.store import Store, User

router = APIRouter(prefix="/account", tags=["account"])


@router.get("", response_model=UserOut)
def me(user: User = Depends(get_user)):
    return user_out(user)


@router.patch("", response_model=UserOut)
def update_me(
    body: ProfileUpdateIn,
    user: User = Depends(get_user),
    conn: Connection = Depends(get_db),
):
    return user_out(auth_service.update_name(conn, user, body.name))


@router.delete("")
def delete_me(
    user: User = Depends(get_user),
    store: Store = Depends(get_store),
    conn: Connection = Depends(get_db),
):
    """Permanently deletes the account and all its data (required by the App Store / Play Store)."""
    auth_service.delete_account(conn, store, user)
    return {}
