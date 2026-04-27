from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import ConfigStore, Settings
from .provider_specs import PROVIDER_TYPES
from .push import DeliveryOptions, NotificationMessage, send_delivery, send_provider
from .scheduler import SchedulerService, parse_schedule_times
from .time_utils import beijing_now


SESSION_COOKIE_NAME = "roco_console_session"
PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
TEMPLATE_DIR = PACKAGE_DIR / "templates"
store = ConfigStore()
scheduler = SchedulerService(store)


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()


app = FastAPI(title="Roco Push Console", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _format_dt(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else "-"


def _auth_password() -> str:
    return os.environ.get("CONSOLE_PASSWORD", "").strip()


def _auth_username() -> str:
    return os.environ.get("CONSOLE_USERNAME", "admin").strip() or "admin"


def _session_ttl() -> int:
    try:
        return max(300, int(os.environ.get("CONSOLE_SESSION_TTL", "86400")))
    except ValueError:
        return 86400


def _session_secret() -> bytes:
    seed = os.environ.get("CONSOLE_SESSION_SECRET") or _auth_password() or "roco-push-console"
    return seed.encode("utf-8")


def _sign_session(username: str, expires_at: int, nonce: str) -> str:
    body = f"{username}|{expires_at}|{nonce}".encode("utf-8")
    return hmac.new(_session_secret(), body, hashlib.sha256).hexdigest()


def _make_session_cookie(username: str) -> str:
    expires_at = int(time.time()) + _session_ttl()
    nonce = secrets.token_urlsafe(12)
    signature = _sign_session(username, expires_at, nonce)
    token = f"{username}|{expires_at}|{nonce}|{signature}".encode("utf-8")
    return base64.urlsafe_b64encode(token).decode("ascii")


def _valid_session_cookie(value: str | None) -> bool:
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
    if not secrets.compare_digest(username, _auth_username()):
        return False
    expected = _sign_session(username, expires_at, nonce)
    return secrets.compare_digest(signature, expected)


def _is_authenticated(request: Request) -> bool:
    password = _auth_password()
    if not password:
        return True
    return _valid_session_cookie(request.cookies.get(SESSION_COOKIE_NAME))


def _require_auth(request: Request) -> None:
    if not _is_authenticated(request):
        raise HTTPException(status_code=401, detail="请先登录控制台")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse | RedirectResponse:
    if exc.status_code == 401 and not request.url.path.startswith("/api/"):
        next_path = request.url.path
        if request.url.query:
            next_path = f"{next_path}?{request.url.query}"
        return RedirectResponse(f"/login?next={quote(next_path, safe='/?:=&')}", status_code=303)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if not _auth_password() or _is_authenticated(request):
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(render_login_html())


@app.post("/api/login")
async def api_login(request: Request) -> JSONResponse:
    if not _auth_password():
        return JSONResponse({"ok": True, "message": "未启用控制台认证"})

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="登录参数格式错误") from exc

    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    valid = secrets.compare_digest(username, _auth_username()) and secrets.compare_digest(password, _auth_password())
    if not valid:
        raise HTTPException(status_code=401, detail="用户名或密码不正确")

    response = JSONResponse({"ok": True, "message": "登录成功"})
    response.set_cookie(
        SESSION_COOKIE_NAME,
        _make_session_cookie(username),
        max_age=_session_ttl(),
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return response


@app.post("/api/logout")
async def api_logout() -> JSONResponse:
    response = JSONResponse({"ok": True, "message": "已退出登录"})
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@app.get("/", response_class=HTMLResponse, dependencies=[Depends(_require_auth)])
async def index() -> str:
    return render_index_html()


@app.get("/api/provider-types", dependencies=[Depends(_require_auth)])
async def api_provider_types() -> dict[str, Any]:
    return {"provider_types": PROVIDER_TYPES}


@app.get("/api/state", dependencies=[Depends(_require_auth)])
async def api_state() -> dict[str, Any]:
    settings = store.load()
    return {
        "config": settings.public_dict(),
        "config_issue": store.load_issue_dict(),
        "provider_types": PROVIDER_TYPES,
        "scheduler": scheduler.state.to_dict(),
        "auth_enabled": bool(_auth_password()),
        "now": beijing_now().isoformat(),
    }


@app.post("/api/config", dependencies=[Depends(_require_auth)])
async def api_save_config(request: Request) -> JSONResponse:
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="配置格式错误")

    schedule_times = str(payload.get("schedule_times", "")).strip()
    try:
        parse_schedule_times(schedule_times)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    providers = payload.get("providers", [])
    if not isinstance(providers, list):
        raise HTTPException(status_code=400, detail="通道配置格式错误")
    for provider in providers:
        if not isinstance(provider, dict):
            raise HTTPException(status_code=400, detail="通道配置格式错误")
        if provider.get("type") not in PROVIDER_TYPES:
            raise HTTPException(status_code=400, detail=f"未知通道类型: {provider.get('type')}")

    try:
        settings = store.update(payload)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"配置保存失败: {exc}") from exc
    scheduler.wake()
    return JSONResponse({"ok": True, "config": settings.public_dict()})


@app.post("/api/run-now", dependencies=[Depends(_require_auth)])
async def api_run_now() -> JSONResponse:
    started = await scheduler.run_now()
    if not started:
        return JSONResponse({"ok": False, "message": "已有任务正在执行"})
    return JSONResponse({"ok": True, "message": "已开始执行"})


@app.post("/api/test-push", dependencies=[Depends(_require_auth)])
async def api_test_push(request: Request) -> JSONResponse:
    payload = await request.json()
    provider_id = str(payload.get("provider_id", "")).strip() if isinstance(payload, dict) else ""
    settings = _settings_from_test_payload(payload)
    message = NotificationMessage(
        "远行商人提醒测试",
        "控制台测试推送成功。",
        f"### 控制台测试推送\n\n北京时间：{_format_dt(beijing_now())}",
    )

    session = requests.Session()
    if provider_id:
        provider = next((item for item in settings.providers if item.id == provider_id), None)
        if provider is None:
            raise HTTPException(status_code=404, detail="通道不存在")
        result = await asyncio.to_thread(
            send_provider,
            provider,
            message,
            session=session,
            timeout=settings.http_timeout,
        )
        if not result.success:
            raise HTTPException(status_code=500, detail=f"测试推送失败: {result.message}")
        return JSONResponse({"ok": True, "message": f"{provider.name} 测试推送已发送", "results": [result.to_dict()]})

    report = await asyncio.to_thread(
        send_delivery,
        settings.providers,
        message,
        options=DeliveryOptions(
            mode=settings.delivery_mode,
            selected_provider=settings.selected_provider,
            failover_order=settings.failover_order,
            session=session,
            timeout=settings.http_timeout,
        ),
    )
    if not report.success:
        raise HTTPException(status_code=500, detail=f"测试推送失败: {report.summary()}")
    return JSONResponse({"ok": True, "message": "测试推送已发送", "results": report.to_dict()["results"]})


def _settings_from_test_payload(payload: Any) -> Settings:
    settings = store.load()
    if not isinstance(payload, dict):
        return settings

    draft_config = payload.get("config")
    if not isinstance(draft_config, dict):
        return settings

    for provider in draft_config.get("providers", []):
        if not isinstance(provider, dict) or provider.get("type") not in PROVIDER_TYPES:
            provider_type = provider.get("type") if isinstance(provider, dict) else provider
            raise HTTPException(status_code=400, detail=f"未知通道类型: {provider_type}")

    return Settings.from_mapping(draft_config, base=settings, keep_blank_secrets=True)


def cli() -> None:
    host = os.environ.get("WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("WEB_PORT", "19892"))
    uvicorn.run("roco_push_console.web:app", host=host, port=port)


def _read_template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def render_login_html() -> str:
    username = escape(_auth_username(), quote=True)
    return _read_template("login.html").replace("__USERNAME__", username)


def render_index_html() -> str:
    return _read_template("index.html")


if __name__ == "__main__":
    cli()
