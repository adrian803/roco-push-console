from __future__ import annotations

import os
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import web_auth, web_services
from .config_store import ConfigStore
from .provider_specs import public_provider_types
from .scheduler import SchedulerService


SESSION_COOKIE_NAME = web_auth.SESSION_COOKIE_NAME
PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
TEMPLATE_DIR = PACKAGE_DIR / "templates"
store = ConfigStore()
scheduler = SchedulerService(store)
static_files = StaticFiles(directory=str(STATIC_DIR))


@asynccontextmanager
async def lifespan(_: FastAPI):
    web_auth.log_console_password_once(store)
    scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()


app = FastAPI(title="Roco Push Console", lifespan=lifespan)


@app.get("/static/{path:path}", include_in_schema=False)
async def static_asset(path: str, request: Request):
    return await static_files.get_response(path, request.scope)


def _require_auth(request: Request) -> None:
    if not web_auth.is_authenticated(store, request):
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
    if not web_auth.auth_enabled(store) or web_auth.is_authenticated(store, request):
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(render_login_html())


@app.post("/api/login")
async def api_login(request: Request) -> JSONResponse:
    if not web_auth.auth_enabled(store):
        if web_auth.allow_empty_password():
            return JSONResponse({"ok": True, "message": "未启用控制台认证"})

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="登录参数格式错误") from exc

    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not web_auth.credentials_are_valid(store, username, password):
        raise HTTPException(status_code=401, detail="用户名或密码不正确")

    response = JSONResponse({"ok": True, "message": "登录成功"})
    response.set_cookie(
        SESSION_COOKIE_NAME,
        web_auth.make_session_cookie(store, username),
        max_age=web_auth.session_ttl(),
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
    return {"provider_types": public_provider_types()}


@app.get("/api/state", dependencies=[Depends(_require_auth)])
async def api_state() -> dict[str, Any]:
    return web_services.build_state_payload(store, scheduler)


@app.post("/api/config", dependencies=[Depends(_require_auth)])
async def api_save_config(request: Request) -> JSONResponse:
    payload = await request.json()
    try:
        settings = web_services.save_config_payload(store, scheduler, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"配置保存失败: {exc}") from exc
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
    try:
        return JSONResponse(await web_services.send_test_push(store, payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def cli() -> None:
    host = os.environ.get("WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("WEB_PORT", "19892"))
    uvicorn.run("roco_serverchan_notifier.web:app", host=host, port=port)


def _read_template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def render_login_html() -> str:
    username = escape(web_auth.auth_username(), quote=True)
    return _read_template("login.html").replace("__USERNAME__", username)


def render_index_html() -> str:
    return _read_template("index.html")


if __name__ == "__main__":
    cli()
