import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

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


def register(store: Store, name: str, identifier: str, password: str) -> AuthResult:
    name = validate_name(name)
    ident = validate_identifier(identifier)
    validate_password(password)
    pw_hash = hash_password(password)  # slow on purpose — done before taking the lock

    with store.lock:
        if ident in store.user_ids_by_identifier:
            raise AppError(
                409,
                "ACCOUNT_EXISTS",
                "An account with this email or phone number already exists. Try logging in.",
            )
        user = User(
            id=new_id(),
            name=name,
            identifier=ident,
            password_hash=pw_hash,
            created_at=store.now(),
        )
        store.users[user.id] = user
        store.user_ids_by_identifier[ident] = user.id
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


def login(store: Store, identifier: str, password: str) -> AuthResult:
    ident = validate_identifier(identifier)
    if not password:
        raise AppError(422, "VALIDATION_ERROR", "Enter your password")

    with store.lock:
        _check_lockout(store, ident, store.now())
        user = store.user_by_identifier(ident)
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
        return _issue_session(store, user)  # type: ignore[arg-type]


def authenticate(store: Store, token: str) -> Principal:
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
        user = store.users.get(session.user_id)
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


def update_name(store: Store, user: User, name: str) -> User:
    clean = validate_name(name)
    with store.lock:
        user.name = clean
        return user


def delete_account(store: Store, user: User) -> None:
    """Removes the account and every piece of personal data tied to it."""
    with store.lock:
        _revoke_all_sessions(store, user.id)
        for key in [k for k, t in store.reset_tokens.items() if t.user_id == user.id]:
            del store.reset_tokens[key]
        for vid in [v.id for v in store.vehicles.values() if v.user_id == user.id]:
            del store.vehicles[vid]
        for bid in [b.id for b in store.bookings.values() if b.user_id == user.id]:
            del store.bookings[bid]
        store.user_ids_by_identifier.pop(user.identifier, None)
        store.login_failures.pop(user.identifier, None)
        store.users.pop(user.id, None)


def request_password_reset(store: Store, identifier: str) -> None:
    """Always succeeds silently so attackers can't discover which accounts exist."""
    ident = validate_identifier(identifier)
    with store.lock:
        user = store.user_by_identifier(ident)
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


def reset_password(store: Store, token: str, new_password: str) -> None:
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
        user = store.users.get(entry.user_id)
        del store.reset_tokens[key]
        if user is None:
            raise AppError(
                400, "INVALID_RESET_TOKEN", "This reset link is invalid or has expired."
            )
        user.password_hash = pw_hash
        store.login_failures.pop(user.identifier, None)
        _revoke_all_sessions(store, user.id)  # sign out everywhere
