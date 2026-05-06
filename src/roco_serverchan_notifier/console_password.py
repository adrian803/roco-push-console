from __future__ import annotations

import base64
import hashlib
import os
import secrets
from typing import Any

from .config_store import ConfigStore
from .time_utils import beijing_now


CONSOLE_PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
CONSOLE_PASSWORD_HASH_ITERATIONS = 260000

_GENERATED_CONSOLE_PASSWORD: str | None = None
_GENERATED_CONSOLE_PASSWORD_CREATED = False
_GENERATED_CONSOLE_PASSWORD_SAVE_ERROR: str | None = None
_CONSOLE_AUTH_CACHE: dict[str, Any] | None = None
_CONSOLE_AUTH_CACHE_STORE_ID: int | None = None
_LOGGED_CONSOLE_PASSWORD = False


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def allow_empty_password() -> bool:
    return _env_bool("CONSOLE_ALLOW_EMPTY_PASSWORD", False)


def configured_auth_password() -> str:
    return os.environ.get("CONSOLE_PASSWORD", "").strip()


def auth_username() -> str:
    return os.environ.get("CONSOLE_USERNAME", "admin").strip() or "admin"


def reset_console_auth_cache() -> None:
    global _CONSOLE_AUTH_CACHE, _CONSOLE_AUTH_CACHE_STORE_ID
    _CONSOLE_AUTH_CACHE = None
    _CONSOLE_AUTH_CACHE_STORE_ID = None


def _set_console_auth_cache(store: ConfigStore, auth: dict[str, Any]) -> None:
    global _CONSOLE_AUTH_CACHE, _CONSOLE_AUTH_CACHE_STORE_ID
    _CONSOLE_AUTH_CACHE = dict(auth)
    _CONSOLE_AUTH_CACHE_STORE_ID = id(store)


def console_auth(store: ConfigStore) -> dict[str, Any]:
    if _CONSOLE_AUTH_CACHE is not None and _CONSOLE_AUTH_CACHE_STORE_ID == id(store):
        return dict(_CONSOLE_AUTH_CACHE)
    auth = store.console_auth()
    _set_console_auth_cache(store, auth)
    return auth


def stored_console_password_hash(store: ConfigStore) -> str:
    auth = console_auth(store)
    return str(auth.get("password_hash") or "").strip()


def hash_console_password(
    password: str,
    *,
    salt: str | None = None,
    iterations: int = CONSOLE_PASSWORD_HASH_ITERATIONS,
) -> str:
    salt = salt or secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{CONSOLE_PASSWORD_HASH_ALGORITHM}${iterations}${salt}${digest_text}"


def verify_console_password_hash(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, _digest = password_hash.split("$", 3)
        iterations = int(iterations_text)
    except ValueError:
        return False
    if algorithm != CONSOLE_PASSWORD_HASH_ALGORITHM or iterations <= 0:
        return False
    expected = hash_console_password(password, salt=salt, iterations=iterations)
    return secrets.compare_digest(password_hash, expected)


def _generated_console_auth(password: str) -> dict[str, str]:
    return {
        "password_hash": hash_console_password(password),
        "generated_at": beijing_now().isoformat(),
    }


def generated_console_password(store: ConfigStore) -> str:
    global _GENERATED_CONSOLE_PASSWORD, _GENERATED_CONSOLE_PASSWORD_CREATED, _GENERATED_CONSOLE_PASSWORD_SAVE_ERROR
    if _GENERATED_CONSOLE_PASSWORD is None:
        if stored_console_password_hash(store):
            return ""
        _GENERATED_CONSOLE_PASSWORD = secrets.token_urlsafe(24)
        _GENERATED_CONSOLE_PASSWORD_CREATED = True
        auth = _generated_console_auth(_GENERATED_CONSOLE_PASSWORD)
        try:
            store.save_console_auth(auth)
        except OSError as exc:
            _GENERATED_CONSOLE_PASSWORD_SAVE_ERROR = str(exc)
        else:
            _GENERATED_CONSOLE_PASSWORD_SAVE_ERROR = None
            _set_console_auth_cache(store, auth)
    return _GENERATED_CONSOLE_PASSWORD


def auth_password(store: ConfigStore) -> str:
    if allow_empty_password():
        return ""
    configured = configured_auth_password()
    if configured:
        return configured
    if _GENERATED_CONSOLE_PASSWORD is not None:
        return _GENERATED_CONSOLE_PASSWORD
    if stored_console_password_hash(store):
        return ""
    return generated_console_password(store)


def auth_enabled(store: ConfigStore) -> bool:
    if allow_empty_password():
        return False
    if configured_auth_password() or stored_console_password_hash(store):
        return True
    return bool(generated_console_password(store))


def check_auth_password(store: ConfigStore, password: str) -> bool:
    configured = configured_auth_password()
    if configured:
        return secrets.compare_digest(password, configured)
    if _GENERATED_CONSOLE_PASSWORD is not None:
        return secrets.compare_digest(password, _GENERATED_CONSOLE_PASSWORD)
    password_hash = stored_console_password_hash(store)
    return bool(password_hash) and verify_console_password_hash(password, password_hash)


def credentials_are_valid(store: ConfigStore, username: str, password: str) -> bool:
    return secrets.compare_digest(username, auth_username()) and check_auth_password(store, password)


def uses_generated_console_password() -> bool:
    return (
        not configured_auth_password()
        and not allow_empty_password()
        and _GENERATED_CONSOLE_PASSWORD_CREATED
    )


def log_console_password_once(store: ConfigStore) -> None:
    global _LOGGED_CONSOLE_PASSWORD
    if _LOGGED_CONSOLE_PASSWORD or configured_auth_password() or allow_empty_password():
        return
    password = auth_password(store)
    if not password or not uses_generated_console_password():
        return
    print("控制台未设置 CONSOLE_PASSWORD，已生成本次启动默认密码：", flush=True)
    print(f"控制台默认密码: {password}", flush=True)
    if _GENERATED_CONSOLE_PASSWORD_SAVE_ERROR:
        print(
            "控制台密码未能保存到 config.json，本次启动临时有效；"
            f"保存失败: {_GENERATED_CONSOLE_PASSWORD_SAVE_ERROR}",
            flush=True,
        )
    else:
        print("密码哈希已保存到 config.json；忘记密码时可删除 console_auth 段重新生成。", flush=True)
    _LOGGED_CONSOLE_PASSWORD = True


def reset_generated_password_for_tests() -> None:
    global _GENERATED_CONSOLE_PASSWORD
    global _GENERATED_CONSOLE_PASSWORD_CREATED
    global _GENERATED_CONSOLE_PASSWORD_SAVE_ERROR
    global _LOGGED_CONSOLE_PASSWORD
    _GENERATED_CONSOLE_PASSWORD = None
    _GENERATED_CONSOLE_PASSWORD_CREATED = False
    _GENERATED_CONSOLE_PASSWORD_SAVE_ERROR = None
    _LOGGED_CONSOLE_PASSWORD = False
    reset_console_auth_cache()
