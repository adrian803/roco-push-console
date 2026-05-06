from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from typing import Any

from .config_store import ConfigStore
from .console_password import (
    allow_empty_password,
    auth_enabled,
    auth_password,
    auth_username,
    configured_auth_password,
    stored_console_password_hash,
)


SESSION_COOKIE_NAME = "roco_console_session"


def session_ttl() -> int:
    try:
        return max(300, int(os.environ.get("CONSOLE_SESSION_TTL", "86400")))
    except ValueError:
        return 86400


def session_secret(store: ConfigStore) -> bytes:
    seed = os.environ.get("CONSOLE_SESSION_SECRET") or configured_auth_password()
    if not seed:
        seed = stored_console_password_hash(store)
    if not seed:
        password = auth_password(store)
        seed = stored_console_password_hash(store) or password or "roco-serverchan-notifier"
    return seed.encode("utf-8")


def sign_session(store: ConfigStore, username: str, expires_at: int, nonce: str) -> str:
    body = f"{username}|{expires_at}|{nonce}".encode("utf-8")
    return hmac.new(session_secret(store), body, hashlib.sha256).hexdigest()


def make_session_cookie(store: ConfigStore, username: str) -> str:
    expires_at = int(time.time()) + session_ttl()
    nonce = secrets.token_urlsafe(12)
    signature = sign_session(store, username, expires_at, nonce)
    token = f"{username}|{expires_at}|{nonce}|{signature}".encode("utf-8")
    return base64.urlsafe_b64encode(token).decode("ascii")


def valid_session_cookie(store: ConfigStore, value: str | None) -> bool:
    if not value:
        return False
    try:
        decoded = base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8")
        username, expires_text, nonce, signature = decoded.split("|", 3)
        expires_at = int(expires_text)
    except (ValueError, UnicodeDecodeError):
        return False
    if expires_at < int(time.time()):
        return False
    if not secrets.compare_digest(username, auth_username()):
        return False
    expected = sign_session(store, username, expires_at, nonce)
    return secrets.compare_digest(signature, expected)


def is_authenticated(store: ConfigStore, request: Any) -> bool:
    if not auth_enabled(store):
        return allow_empty_password()
    return valid_session_cookie(store, request.cookies.get(SESSION_COOKIE_NAME))
