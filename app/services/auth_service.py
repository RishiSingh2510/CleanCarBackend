import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row

from app.domain.scheduling import IST
from app.domain.validation import validate_identifier, validate_name, validate_password
from app.errors import AppError
from app.security import (
    DUMMY_HASH,
    hash_password,
    hash_token,
    new_token,
    verify_password,
)
from app.store import ResetToken, Session, Store, User, new_id

log = logging.getLogger("cleancar")

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15
RESET_TOKEN_MINUTES = 30


@dataclass
class AuthResult:
    token: str
    user: User
    expires_at: datetime


@dataclass
class Principal:
    """Who is making the current request."""

    user: User
    token_hash: str


def _issue_session(store: Store, user: User) -> AuthResult:
    now = store.now()
    # drop this user's expired sessions while we're here
    for key in [
        k
        for k, s in store.sessions.items()
        if s.user_id == user.id and s.expires_at <= now
    ]:
        del store.sessions[key]
    token = new_token()
    expires = now + timedelta(days=store.settings.session_days)
    store.sessions[hash_token(token)] = Session(user_id=user.id, expires_at=expires)
    return AuthResult(token=token, user=user, expires_at=expires)


def _revoke_all_sessions(store: Store, user_id: str) -> None:
    for key in [k for k, s in store.sessions.items() if s.user_id == user_id]:
        del store.sessions[key]


def _user(row: dict[str, Any]) -> User:
    created_at = row["created_at"]
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=IST)
    return User(
        id=str(row["id"]),
        name=row["name"],
        identifier=row["identifier"],
        password_hash=row["password_hash"],
        created_at=created_at,
    )


def _get_user_by_identifier(conn: Connection, identifier: str) -> User | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, name, identifier, password_hash, created_at
            FROM public."Users"
            WHERE identifier = %s
            """,
            (identifier,),
        )
        row = cur.fetchone()
    return _user(row) if row is not None else None


def _get_user_by_id(conn: Connection, user_id: str) -> User | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, name, identifier, password_hash, created_at
            FROM public."Users"
            WHERE id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
    return _user(row) if row is not None else None


def register(
    conn: Connection, store: Store, name: str, identifier: str, password: str
) -> AuthResult:
    name = validate_name(name)
    ident = validate_identifier(identifier)
    validate_password(password)
    pw_hash = hash_password(password)  # slow on purpose — done before taking the lock

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT EXISTS(
                SELECT 1 FROM public."Users" WHERE identifier = %s
            ) AS account_exists
            """,
            (ident,),
        )
        if cur.fetchone()["account_exists"]:
            raise AppError(
                409,
                "ACCOUNT_EXISTS",
                "An account with this email or phone number already exists. Try logging in.",
            )
        cur.execute(
            """
            INSERT INTO public."Users" (id, name, identifier, password_hash, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, name, identifier, password_hash, created_at
            """,
            (new_id(), name, ident, pw_hash, store.now()),
        )
        user = _user(cur.fetchone())
    with store.lock:
        return _issue_session(store, user)


def _check_lockout(store: Store, ident: str, now: datetime) -> None:
    window = now - timedelta(minutes=LOCKOUT_MINUTES)
    recent = [t for t in store.login_failures.get(ident, []) if t > window]
    store.login_failures[ident] = recent
    if len(recent) >= MAX_FAILED_LOGINS:
        wait = max(
            1,
            int(
                (recent[0] + timedelta(minutes=LOCKOUT_MINUTES) - now).total_seconds()
                // 60
            )
            + 1,
        )
        raise AppError(
            429,
            "TOO_MANY_ATTEMPTS",
            f"Too many failed attempts. Please try again in {wait} minute{'s' if wait != 1 else ''}.",
        )


def login(
    conn: Connection, store: Store, identifier: str, password: str
) -> AuthResult:
    ident = validate_identifier(identifier)
    if not password:
        raise AppError(422, "VALIDATION_ERROR", "Enter your password")

    with store.lock:
        _check_lockout(store, ident, store.now())
    user = _get_user_by_identifier(conn, ident)
    stored_hash = user.password_hash if user else DUMMY_HASH

    ok = (
        verify_password(password, stored_hash) and user is not None
    )  # slow check happens outside the lock

    with store.lock:
        if not ok:
            store.login_failures.setdefault(ident, []).append(store.now())
            # same message whether the account exists or not
            raise AppError(
                401, "INVALID_CREDENTIALS", "Incorrect email/phone or password."
            )
        store.login_failures.pop(ident, None)
        return _issue_session(store, user)


def authenticate(conn: Connection, store: Store, token: str) -> Principal:
    key = hash_token(token)
    with store.lock:
        session = store.sessions.get(key)
        if session is None:
            raise AppError(
                401,
                "INVALID_TOKEN",
                "Please sign in again.",
                {"WWW-Authenticate": "Bearer"},
            )
        if session.expires_at <= store.now():
            del store.sessions[key]
            raise AppError(
                401,
                "SESSION_EXPIRED",
                "Your session has expired. Please sign in again.",
                {"WWW-Authenticate": "Bearer"},
            )
        user = _get_user_by_id(conn, session.user_id)
        if user is None:
            del store.sessions[key]
            raise AppError(
                401,
                "INVALID_TOKEN",
                "Please sign in again.",
                {"WWW-Authenticate": "Bearer"},
            )
        return Principal(user=user, token_hash=key)


def logout(store: Store, principal: Principal) -> None:
    with store.lock:
        store.sessions.pop(principal.token_hash, None)


def update_name(conn: Connection, user: User, name: str) -> User:
    clean = validate_name(name)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            UPDATE public."Users"
            SET name = %s
            WHERE id = %s
            RETURNING id, name, identifier, password_hash, created_at
            """,
            (clean, user.id),
        )
        row = cur.fetchone()
    if row is None:
        raise AppError(404, "ACCOUNT_NOT_FOUND", "We couldn't find that account.")
    return _user(row)


def delete_account(conn: Connection, store: Store, user: User) -> None:
    """Removes the account and every piece of personal data tied to it."""
    with conn.cursor() as cur:
        cur.execute('DELETE FROM public."Vehicles" WHERE user_id = %s', (user.id,))
        cur.execute('DELETE FROM public."Users" WHERE id = %s RETURNING id', (user.id,))
        if cur.fetchone() is None:
            raise AppError(404, "ACCOUNT_NOT_FOUND", "We couldn't find that account.")
    with store.lock:
        _revoke_all_sessions(store, user.id)
        for key in [k for k, t in store.reset_tokens.items() if t.user_id == user.id]:
            del store.reset_tokens[key]
        for vid in [v.id for v in store.vehicles.values() if v.user_id == user.id]:
            del store.vehicles[vid]
        for bid in [b.id for b in store.bookings.values() if b.user_id == user.id]:
            del store.bookings[bid]
        store.login_failures.pop(user.identifier, None)
        store.users.pop(user.id, None)


def request_password_reset(conn: Connection, store: Store, identifier: str) -> None:
    """Always succeeds silently so attackers can't discover which accounts exist."""
    ident = validate_identifier(identifier)
    user = _get_user_by_identifier(conn, ident)
    with store.lock:
        if user is None:
            return
        token = new_token()
        store.reset_tokens[hash_token(token)] = ResetToken(
            user_id=user.id,
            expires_at=store.now() + timedelta(minutes=RESET_TOKEN_MINUTES),
        )
    if not store.settings.is_production:
        # No email/SMS provider is connected. In development the token is printed so you can test the flow.
        log.warning("DEV ONLY — password reset token for %s: %s", ident, token)
    # TODO(production): send `token` to the user by email/SMS instead of logging it.


def reset_password(
    conn: Connection, store: Store, token: str, new_password: str
) -> None:
    validate_password(new_password)
    pw_hash = hash_password(new_password)
    key = hash_token(token)
    with store.lock:
        entry = store.reset_tokens.get(key)
        if entry is None or entry.expires_at <= store.now():
            store.reset_tokens.pop(key, None)
            raise AppError(
                400, "INVALID_RESET_TOKEN", "This reset link is invalid or has expired."
            )
        user = _get_user_by_id(conn, entry.user_id)
        del store.reset_tokens[key]
        if user is None:
            raise AppError(
                400, "INVALID_RESET_TOKEN", "This reset link is invalid or has expired."
            )
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE public."Users" SET password_hash = %s WHERE id = %s',
                (pw_hash, user.id),
            )
        store.login_failures.pop(user.identifier, None)
        _revoke_all_sessions(store, user.id)  # sign out everywhere
