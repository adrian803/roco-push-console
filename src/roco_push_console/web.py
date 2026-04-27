from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime
from html import escape
from typing import Any
from urllib.parse import quote

import requests
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from .config import ConfigStore, Settings
from .provider_specs import PROVIDER_TYPES
from .push import NotificationMessage, send_delivery, send_provider
from .scheduler import SchedulerService, parse_schedule_times
from .time_utils import beijing_now


SESSION_COOKIE_NAME = "roco_console_session"
store = ConfigStore()
scheduler = SchedulerService(store)
app = FastAPI(title="Roco Push Console")


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


@app.on_event("startup")
async def startup() -> None:
    scheduler.start()


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
    return INDEX_HTML


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

    for provider in payload.get("providers", []):
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
        mode=settings.delivery_mode,
        selected_provider=settings.selected_provider,
        failover_order=settings.failover_order,
        session=session,
        timeout=settings.http_timeout,
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
            raise HTTPException(status_code=400, detail=f"未知通道类型: {provider.get('type') if isinstance(provider, dict) else provider}")

    return Settings.from_mapping(draft_config, base=settings, keep_blank_secrets=True)


def cli() -> None:
    host = os.environ.get("WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("WEB_PORT", "19892"))
    uvicorn.run("roco_push_console.web:app", host=host, port=port)


def render_login_html() -> str:
    return LOGIN_HTML_TEMPLATE.replace("__USERNAME__", escape(_auth_username(), quote=True))


LOGIN_HTML_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>登录远行商人推送控制台</title>
  <link rel="icon" href='data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"%3E%3Crect width="64" height="64" rx="16" fill="%230071e3"/%3E%3Cpath d="M18 36h28v10H18zM22 20h20v10H22z" fill="white"/%3E%3C/svg%3E'>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f5f7;
      --panel: rgba(255,255,255,.82);
      --panel-strong: rgba(255,255,255,.94);
      --ink: #1d1d1f;
      --muted: #6e6e73;
      --line: rgba(0,0,0,.12);
      --soft-line: rgba(0,0,0,.07);
      --accent: #0071e3;
      --accent-dark: #0057b8;
      --ok: #1f8f55;
      --danger: #c13b2a;
      --shadow: 0 34px 90px rgba(0,0,0,.14);
      --soft-shadow: 0 12px 32px rgba(0,0,0,.08);
    }
    * { box-sizing: border-box; }
    body {
      min-height: 100vh;
      margin: 0;
      display: grid;
      place-items: center;
      padding: 28px;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Microsoft YaHei", sans-serif;
      background:
        linear-gradient(135deg, rgba(0,113,227,.08), transparent 34%),
        linear-gradient(225deg, rgba(52,199,89,.08), transparent 32%),
        linear-gradient(180deg, #fbfbfd 0%, #f5f5f7 52%, #efeff4 100%),
        var(--bg);
      color: var(--ink);
      letter-spacing: 0;
    }
    .login-shell {
      width: min(100%, 920px);
      display: grid;
      gap: 14px;
    }
    .login-card {
      display: grid;
      grid-template-columns: minmax(0, .92fr) minmax(340px, .72fr);
      overflow: hidden;
      border: 1px solid rgba(255,255,255,.78);
      border-radius: 34px;
      background: rgba(255,255,255,.52);
      box-shadow: var(--shadow);
      backdrop-filter: blur(28px) saturate(1.2);
      -webkit-backdrop-filter: blur(28px) saturate(1.2);
    }
    .brand, .panel { min-height: 520px; }
    .brand {
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 34px;
      background:
        linear-gradient(150deg, rgba(255,255,255,.72), rgba(255,255,255,.28)),
        linear-gradient(180deg, rgba(0,113,227,.08), rgba(255,255,255,0));
      border-right: 1px solid var(--soft-line);
    }
    .brand::after {
      content: "";
      position: absolute;
      inset: auto 34px 30px 34px;
      height: 1px;
      background: linear-gradient(90deg, transparent, rgba(0,0,0,.12), transparent);
    }
    .brand-top { display: grid; gap: 20px; align-content: start; }
    .app-icon {
      width: 70px;
      height: 70px;
      border-radius: 22px;
      display: grid;
      place-items: center;
      background: linear-gradient(145deg, #0a84ff, #0066cc);
      box-shadow: 0 20px 44px rgba(0,113,227,.30), inset 0 1px 0 rgba(255,255,255,.42);
    }
    .app-icon svg { width: 42px; height: 42px; fill: #fff; }
    .eyebrow {
      width: fit-content;
      padding: 6px 11px;
      border: 1px solid rgba(0,113,227,.18);
      border-radius: 999px;
      background: rgba(255,255,255,.74);
      color: var(--accent-dark);
      font-size: 12px;
      font-weight: 650;
      box-shadow: 0 1px 0 rgba(255,255,255,.76) inset;
    }
    h1 { margin: 0; max-width: 8em; font-size: 34px; line-height: 1.12; font-weight: 730; }
    .sub { max-width: 28em; color: var(--muted); font-size: 15px; line-height: 1.65; }
    .brand-bottom {
      position: relative;
      display: grid;
      gap: 10px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }
    .status-pill {
      width: fit-content;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border: 1px solid var(--soft-line);
      border-radius: 999px;
      background: rgba(255,255,255,.76);
      color: var(--ink);
      box-shadow: var(--soft-shadow);
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--ok);
      box-shadow: 0 0 0 4px rgba(31,143,85,.12);
    }
    .panel {
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding: 38px;
      background: var(--panel-strong);
    }
    .form-head { display: grid; gap: 7px; margin-bottom: 24px; }
    .form-title { font-size: 24px; font-weight: 720; line-height: 1.2; }
    .form-sub { color: var(--muted); font-size: 14px; line-height: 1.55; }
    form { display: grid; gap: 15px; }
    label { display: grid; gap: 8px; color: var(--muted); font-size: 13px; font-weight: 550; }
    input {
      width: 100%;
      height: 48px;
      border: 1px solid var(--soft-line);
      border-radius: 15px;
      padding: 0 14px;
      background: rgba(255,255,255,.92);
      color: var(--ink);
      font-size: 15px;
      outline: none;
      box-shadow: 0 1px 0 rgba(255,255,255,.88) inset;
      transition: border-color .16s ease, box-shadow .16s ease, background .16s ease;
    }
    input:focus {
      border-color: rgba(0,113,227,.55);
      background: #fff;
      box-shadow: 0 0 0 4px rgba(0,113,227,.12);
    }
    button {
      height: 48px;
      border: 0;
      border-radius: 999px;
      background: var(--accent);
      color: #fff;
      font-size: 15px;
      font-weight: 650;
      cursor: pointer;
      box-shadow: 0 12px 26px rgba(0,113,227,.22);
      transition: transform .16s ease, box-shadow .16s ease, opacity .16s ease;
    }
    button:hover { transform: translateY(-1px); box-shadow: 0 16px 34px rgba(0,113,227,.26); }
    button:disabled { opacity: .58; cursor: wait; transform: none; }
    .message {
      min-height: 21px;
      color: var(--danger);
      font-size: 13px;
      line-height: 1.45;
      text-align: center;
    }
    .footnote {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.55;
      text-align: center;
      padding: 0 16px;
    }
    @media (max-width: 760px) {
      body { padding: 18px; place-items: start center; }
      .login-card { grid-template-columns: 1fr; border-radius: 28px; }
      .brand, .panel { min-height: auto; }
      .brand { padding: 26px; gap: 24px; border-right: 0; border-bottom: 1px solid var(--soft-line); }
      .brand::after { display: none; }
      .panel { padding: 26px; }
      h1 { max-width: none; font-size: 28px; }
      .sub { font-size: 14px; }
    }
    @media (max-width: 420px) {
      body { padding: 12px; }
      .login-card { border-radius: 24px; }
      .brand, .panel { padding: 22px; }
      .app-icon { width: 60px; height: 60px; border-radius: 18px; }
      .app-icon svg { width: 36px; height: 36px; }
    }
  </style>
</head>
<body>
  <main class="login-shell">
    <section class="login-card" aria-label="控制台登录">
      <div class="brand">
        <div class="brand-top">
          <div class="app-icon" aria-hidden="true">
            <svg viewBox="0 0 64 64"><path d="M18 36h28v10H18zM22 20h20v10H22z"/></svg>
          </div>
          <div class="eyebrow">Docker 控制台 · 19892</div>
          <div>
            <h1>远行商人推送控制台</h1>
            <div class="sub">管理定时任务、数据接口与多通道推送。</div>
          </div>
        </div>
        <div class="brand-bottom">
          <div class="status-pill"><span class="status-dot"></span><span>本地会话保护已启用</span></div>
          <div>建议仅在可信网络中访问控制台，并为容器设置独立密码。</div>
        </div>
      </div>
      <div class="panel">
        <div class="form-head">
          <div class="form-title">访问验证</div>
          <div class="form-sub">输入控制台账号后继续。</div>
        </div>
        <form id="loginForm">
          <label>
            用户名
            <input id="username" autocomplete="username" value="__USERNAME__">
          </label>
          <label>
            密码
            <input id="password" type="password" autocomplete="current-password" autofocus>
          </label>
          <button id="loginBtn" type="submit">登录控制台</button>
          <div id="message" class="message" role="status" aria-live="polite"></div>
        </form>
      </div>
    </section>
    <div class="footnote">会话凭据使用 HttpOnly Cookie 保存。密码为空时会关闭认证。</div>
  </main>
  <script>
    const form = document.getElementById("loginForm");
    const button = document.getElementById("loginBtn");
    const message = document.getElementById("message");
    function nextUrl() {
      const params = new URLSearchParams(window.location.search);
      const next = params.get("next") || "/";
      return next.startsWith("/") ? next : "/";
    }
    form.addEventListener("submit", async event => {
      event.preventDefault();
      button.disabled = true;
      message.textContent = "";
      try {
        const response = await fetch("/api/login", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            username: document.getElementById("username").value.trim(),
            password: document.getElementById("password").value,
          }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || data.message || "登录失败");
        window.location.assign(nextUrl());
      } catch (error) {
        message.textContent = error.message;
      } finally {
        button.disabled = false;
      }
    });
  </script>
</body>
</html>"""


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>远行商人推送控制台</title>
  <link rel="icon" href='data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"%3E%3Crect width="64" height="64" rx="16" fill="%230071e3"/%3E%3Cpath d="M18 36h28v10H18zM22 20h20v10H22z" fill="white"/%3E%3C/svg%3E'>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f5f7;
      --panel: rgba(255,255,255,.84);
      --panel-solid: #ffffff;
      --ink: #1d1d1f;
      --muted: #6e6e73;
      --line: rgba(0,0,0,.12);
      --soft-line: rgba(0,0,0,.07);
      --accent: #0071e3;
      --accent-2: #bf5b00;
      --danger: #c13b2a;
      --ok: #1f8f55;
      --shadow: 0 18px 55px rgba(0,0,0,.08);
      --soft-shadow: 0 8px 24px rgba(0,0,0,.06);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-width: 320px;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Microsoft YaHei", sans-serif;
      background:
        radial-gradient(circle at 18% 0%, rgba(0,113,227,.12), transparent 30%),
        radial-gradient(circle at 92% 12%, rgba(52,199,89,.10), transparent 26%),
        linear-gradient(180deg, #fbfbfd 0%, #f5f5f7 46%, #efeff4 100%),
        var(--bg);
      color: var(--ink);
      letter-spacing: 0;
    }
    .shell { max-width: 1240px; margin: 0 auto; padding: 30px 20px 42px; }
    header {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 16px;
      align-items: end;
      padding: 18px 0 22px;
    }
    h1 { margin: 0; font-size: 32px; line-height: 1.12; font-weight: 700; }
    .sub { margin-top: 9px; color: var(--muted); font-size: 14px; }
    .status-strip, .actions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    .status-strip { justify-content: flex-end; }
    .badge {
      min-height: 30px;
      padding: 6px 11px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255,255,255,.74);
      font-size: 13px;
      color: var(--muted);
      white-space: nowrap;
      box-shadow: 0 1px 0 rgba(255,255,255,.75) inset;
    }
    .badge.ok { color: var(--ok); border-color: rgba(31,143,85,.28); background: rgba(237,250,242,.82); }
    .badge.warn { color: var(--accent-2); border-color: rgba(191,91,0,.25); background: rgba(255,247,237,.86); }
    .notice {
      margin-bottom: 14px;
      padding: 12px 14px;
      border: 1px solid rgba(193,59,42,.26);
      border-radius: 8px;
      background: rgba(255,241,236,.88);
      color: var(--danger);
      font-size: 13px;
      line-height: 1.55;
      overflow-wrap: anywhere;
    }
    [hidden] { display: none !important; }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(330px, .65fr);
      gap: 20px;
      margin-top: 8px;
      align-items: start;
    }
    section, .provider-card {
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      border-radius: 8px;
      padding: 20px;
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
    }
    .section-title, .provider-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 14px;
    }
    h2 { margin: 0; font-size: 18px; line-height: 1.2; font-weight: 650; }
    h3 { margin: 0; font-size: 15px; font-weight: 650; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .field { display: grid; gap: 7px; }
    label { font-size: 13px; color: var(--muted); }
    input, select {
      width: 100%;
      height: 42px;
      border: 1px solid var(--soft-line);
      background: rgba(255,255,255,.9);
      color: var(--ink);
      padding: 0 13px;
      font-size: 14px;
      border-radius: 12px;
      outline: none;
      box-shadow: 0 1px 0 rgba(255,255,255,.88) inset;
      transition: border-color .16s ease, box-shadow .16s ease, background .16s ease;
    }
    input:focus, select:focus {
      border-color: rgba(0,113,227,.55);
      background: #fff;
      box-shadow: 0 0 0 4px rgba(0,113,227,.12);
    }
    .checkline { display: flex; align-items: center; gap: 9px; min-height: 40px; padding-top: 21px; }
    .checkline input { width: 18px; height: 18px; }
    .actions { margin-top: 16px; }
    button {
      min-height: 40px;
      border: 1px solid var(--soft-line);
      border-radius: 999px;
      background: rgba(255,255,255,.9);
      color: var(--ink);
      padding: 0 16px;
      font-size: 14px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 7px;
      box-shadow: var(--soft-shadow);
      transition: transform .16s ease, box-shadow .16s ease, background .16s ease;
    }
    button:hover { transform: translateY(-1px); box-shadow: 0 12px 28px rgba(0,0,0,.08); }
    button.primary { background: var(--accent); color: white; border-color: var(--accent); font-weight: 650; }
    button.subtle { border-color: var(--soft-line); color: var(--muted); box-shadow: none; }
    button.danger { border-color: rgba(193,59,42,.25); color: var(--danger); box-shadow: none; }
    button:disabled { opacity: .55; cursor: wait; }
    button:disabled:hover { transform: none; box-shadow: var(--soft-shadow); }
    .providers { display: grid; gap: 12px; margin-top: 14px; }
    .provider-card {
      box-shadow: none;
      background: rgba(255,255,255,.72);
      border-color: var(--soft-line);
      border-left: 4px solid rgba(0,113,227,.35);
    }
    .provider-meta { color: var(--muted); font-size: 13px; margin-top: 3px; }
    .kv { display: grid; gap: 11px; }
    .row {
      display: grid;
      grid-template-columns: 104px 1fr;
      gap: 10px;
      padding: 10px 0;
      border-bottom: 1px solid var(--soft-line);
      font-size: 14px;
    }
    .row span:first-child { color: var(--muted); }
    .logbox {
      min-height: 78px;
      padding: 13px 14px;
      border-radius: 8px;
      background: #1d1d1f;
      color: #f5f5f7;
      font-family: Consolas, "Cascadia Mono", monospace;
      font-size: 13px;
      overflow-wrap: anywhere;
      white-space: pre-wrap;
    }
    .result-heading { margin-top: 15px; font-size: 13px; color: var(--muted); }
    .result-list { display: grid; gap: 8px; margin-top: 8px; }
    .result-item {
      border: 1px solid var(--line);
      border-left: 4px solid var(--line);
      border-radius: 8px;
      padding: 11px 12px;
      font-size: 13px;
      background: rgba(255,255,255,.82);
    }
    .result-item.ok { border-left-color: var(--ok); }
    .result-item.fail { border-left-color: var(--danger); }
    .result-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
    .result-status { font-size: 12px; color: var(--muted); white-space: nowrap; }
    .result-item.ok .result-status { color: var(--ok); }
    .result-item.fail .result-status { color: var(--danger); }
    .result-message { margin-top: 6px; color: var(--muted); line-height: 1.45; overflow-wrap: anywhere; }
    .empty-state {
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 12px;
      color: var(--muted);
      background: rgba(255,255,255,.55);
      font-size: 13px;
    }
    .mono { font-family: Consolas, "Cascadia Mono", monospace; }
    @media (max-width: 900px) {
      header, main, .grid { grid-template-columns: 1fr; }
      .status-strip { justify-content: flex-start; }
      .checkline { padding-top: 0; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>远行商人推送控制台</h1>
        <div class="sub">插件化推送 · Docker 常驻调度 · 多通道同时发 / 单选 / 主备切换</div>
      </div>
      <div class="status-strip">
        <span id="configuredBadge" class="badge warn">未配置</span>
        <span id="runningBadge" class="badge">调度器</span>
        <span id="nowBadge" class="badge mono">--:--</span>
        <button id="logoutBtn" class="subtle" type="button">退出</button>
      </div>
    </header>

    <main>
      <div>
        <section>
          <div class="section-title">
            <h2>基础配置</h2>
            <div class="status-strip">
              <span id="draftBadge" class="badge warn" hidden>有未保存修改</span>
              <span class="badge">保存后立即重算下次执行</span>
            </div>
          </div>
          <form id="configForm">
            <div class="grid">
              <div class="field">
                <label for="rocom_api_key">ROCOM API Key</label>
                <input id="rocom_api_key" name="rocom_api_key" type="password" autocomplete="off">
              </div>
              <div class="field">
                <label for="game_api_url">数据接口</label>
                <input id="game_api_url" name="game_api_url" type="url">
              </div>
              <div class="field">
                <label for="schedule_times">北京时间定时</label>
                <input id="schedule_times" name="schedule_times" class="mono" placeholder="08:01,12:01,16:01,20:01">
              </div>
              <div class="field">
                <label for="http_timeout">请求超时秒数</label>
                <input id="http_timeout" name="http_timeout" type="number" min="1" max="300">
              </div>
              <div class="field">
                <label for="delivery_mode">发送策略</label>
                <select id="delivery_mode" name="delivery_mode">
                  <option value="all">所有启用通道同时发送</option>
                  <option value="single">只发送选中通道</option>
                  <option value="failover">主备切换，成功即停</option>
                </select>
              </div>
              <div class="field">
                <label for="selected_provider">选中通道</label>
                <select id="selected_provider" name="selected_provider"></select>
              </div>
              <label class="checkline">
                <input id="notify_empty" name="notify_empty" type="checkbox">
                无商品时也推送
              </label>
              <label class="checkline">
                <input id="run_on_start" name="run_on_start" type="checkbox">
                容器启动后立即执行
              </label>
            </div>

            <div class="section-title" style="margin-top: 22px;">
              <h2>通道配置</h2>
              <div class="actions" style="margin-top: 0;">
                <select id="newProviderType"></select>
                <button id="addProviderBtn" type="button">添加通道</button>
              </div>
            </div>
            <div id="providers" class="providers"></div>

            <div class="actions">
              <button id="saveBtn" class="primary" type="submit">保存配置</button>
              <button id="runBtn" type="button">立即执行</button>
              <button id="testBtn" class="subtle" type="button">按策略测试</button>
              <button id="refreshBtn" class="subtle" type="button">刷新状态</button>
            </div>
          </form>
        </section>
      </div>

      <section>
        <div class="section-title">
          <h2>状态</h2>
          <span id="busyBadge" class="badge">空闲</span>
        </div>
        <div id="configIssue" class="notice" hidden></div>
        <div class="kv">
          <div class="row"><span>下次执行</span><strong id="nextRun">-</strong></div>
          <div class="row"><span>上次开始</span><strong id="lastStart">-</strong></div>
          <div class="row"><span>上次结束</span><strong id="lastFinish">-</strong></div>
          <div class="row"><span>状态码</span><strong id="lastCode">-</strong></div>
        </div>
        <div class="actions">
          <div id="message" class="logbox">等待状态刷新</div>
        </div>
        <div class="result-heading">最近推送结果</div>
        <div id="pushResults" class="result-list"></div>
      </section>
    </main>
  </div>

  <script>
    const $ = (id) => document.getElementById(id);
    const baseFields = ["rocom_api_key", "game_api_url", "schedule_times", "http_timeout", "delivery_mode", "selected_provider"];
    let providerTypes = {};
    let providers = [];
    let configDirty = false;

    function newId(type) {
      return `${type}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
    }
    function prettyTime(value) {
      if (!value) return "-";
      return value.replace("T", " ").replace("+08:00", "");
    }
    function escapeHTML(value) {
      return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;",
      }[char]));
    }
    async function requestJSON(url, options = {}) {
      const response = await fetch(url, {
        headers: {"Content-Type": "application/json"},
        ...options,
      });
      const text = await response.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch (error) {
        data = {message: text || "请求失败"};
      }
      if (!response.ok) throw new Error(data.detail || data.message || "请求失败");
      return data;
    }
    function setBusy(isBusy) {
      ["saveBtn", "runBtn", "testBtn", "refreshBtn", "addProviderBtn"].forEach(id => $(id).disabled = isBusy);
    }
    function updateDraftBadge() {
      $("draftBadge").hidden = !configDirty;
    }
    function markConfigDirty() {
      configDirty = true;
      updateDraftBadge();
    }
    function clearConfigDirty() {
      configDirty = false;
      updateDraftBadge();
    }
    function renderConfigIssue(issue) {
      const box = $("configIssue");
      if (!issue || !issue.message) {
        box.hidden = true;
        box.textContent = "";
        return;
      }
      box.hidden = false;
      box.textContent = issue.backup_path ? `${issue.message}` : issue.message;
    }
    function renderPushResults(results) {
      const host = $("pushResults");
      host.textContent = "";
      if (!results || !results.length) {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent = "本轮暂无推送结果";
        host.appendChild(empty);
        return;
      }
      results.forEach(result => {
        const item = document.createElement("div");
        item.className = `result-item ${result.success ? "ok" : "fail"}`;
        const head = document.createElement("div");
        head.className = "result-head";
        const title = document.createElement("strong");
        title.textContent = result.provider_name || result.provider_type || "推送通道";
        const status = document.createElement("span");
        status.className = "result-status";
        status.textContent = result.success ? "成功" : "失败";
        head.append(title, status);

        const message = document.createElement("div");
        message.className = "result-message";
        const statusCode = result.status_code ? `HTTP ${result.status_code} · ` : "";
        message.textContent = `${statusCode}${result.message || "无详情"}`;
        item.append(head, message);
        host.appendChild(item);
      });
    }
    function providerLabel(type) {
      return (providerTypes[type] && providerTypes[type].label) || type;
    }
    function renderProviderTypeOptions() {
      $("newProviderType").innerHTML = Object.entries(providerTypes).map(([type, spec]) =>
        `<option value="${escapeHTML(type)}">${escapeHTML(spec.label)}</option>`
      ).join("");
    }
    function refreshProviderSelects(config = {}) {
      const options = ['<option value="">未选择</option>'].concat(providers.map(provider =>
        `<option value="${escapeHTML(provider.id)}">${escapeHTML(provider.name || providerLabel(provider.type))}</option>`
      ));
      $("selected_provider").innerHTML = options.join("");
      $("selected_provider").value = config.selected_provider || "";
    }
    function renderProviders() {
      const host = $("providers");
      if (!providers.length) {
        host.innerHTML = `<div class="provider-card"><div class="empty-state">还没有通道，先从右上角添加一个。</div></div>`;
        refreshProviderSelects();
        return;
      }
      host.innerHTML = providers.map((provider, index) => {
        const spec = providerTypes[provider.type] || {fields: [], label: provider.type, description: ""};
        const fields = spec.fields.map(field => {
          const value = provider.config[field.name] ?? "";
          const hasValue = provider.config[`has_${field.name}`];
          const placeholder = field.secret && hasValue ? "已配置，留空不改" : (field.default || "");
          return `
            <div class="field">
              <label>${escapeHTML(field.label)}${field.required ? " *" : ""}</label>
              <input data-provider-index="${index}" data-config-field="${escapeHTML(field.name)}" type="${field.secret ? "password" : "text"}" value="${escapeHTML(value || "")}" placeholder="${escapeHTML(placeholder)}">
            </div>`;
        }).join("");
        return `
          <div class="provider-card" data-provider-index="${index}">
            <div class="provider-head">
              <div>
                <h3>${escapeHTML(provider.name || spec.label)}</h3>
                <div class="provider-meta">${escapeHTML(spec.label)} · ${escapeHTML(spec.description || "")}</div>
              </div>
              <div class="actions" style="margin-top:0;">
                <button type="button" class="subtle" data-action="move-up" data-index="${index}" ${index === 0 ? "disabled" : ""}>上移</button>
                <button type="button" class="subtle" data-action="move-down" data-index="${index}" ${index === providers.length - 1 ? "disabled" : ""}>下移</button>
                <button type="button" class="subtle" data-action="test" data-index="${index}">测试</button>
                <button type="button" class="danger" data-action="remove" data-index="${index}">删除</button>
              </div>
            </div>
            <div class="grid">
              <div class="field">
                <label>名称</label>
                <input data-provider-index="${index}" data-provider-field="name" value="${escapeHTML(provider.name || "")}">
              </div>
              <label class="checkline">
                <input data-provider-index="${index}" data-provider-field="enabled" type="checkbox" ${provider.enabled ? "checked" : ""}>
                启用
              </label>
              ${fields}
            </div>
          </div>`;
      }).join("");
      refreshProviderSelects({selected_provider: $("selected_provider").value});
    }
    function collectProviders() {
      const next = providers.map(provider => ({
        id: provider.id,
        type: provider.type,
        name: provider.name,
        enabled: provider.enabled,
        config: {...provider.config},
      }));
      document.querySelectorAll("[data-provider-index]").forEach(input => {
        const index = Number(input.dataset.providerIndex);
        if (!next[index]) return;
        if (input.dataset.providerField) {
          const name = input.dataset.providerField;
          next[index][name] = input.type === "checkbox" ? input.checked : input.value.trim();
        }
        if (input.dataset.configField) {
          next[index].config[input.dataset.configField] = input.value.trim();
        }
      });
      return next;
    }
    function buildConfigPayload() {
      providers = collectProviders();
      return {
        rocom_api_key: $("rocom_api_key").value,
        game_api_url: $("game_api_url").value,
        schedule_times: $("schedule_times").value,
        http_timeout: Number($("http_timeout").value || 30),
        notify_empty: $("notify_empty").checked,
        run_on_start: $("run_on_start").checked,
        delivery_mode: $("delivery_mode").value,
        selected_provider: $("selected_provider").value,
        failover_order: providers.filter(provider => provider.enabled).map(provider => provider.id),
        providers,
      };
    }
    function applyConfig(config) {
      providers = config.providers || [];
      baseFields.forEach(name => {
        if (name === "rocom_api_key") {
          $(name).value = "";
          $(name).placeholder = config.has_rocom_api_key ? "已配置，留空不改" : "未配置";
        } else if (name !== "selected_provider") {
          $(name).value = config[name] ?? "";
        }
      });
      $("notify_empty").checked = !!config.notify_empty;
      $("run_on_start").checked = !!config.run_on_start;
      renderProviders();
      refreshProviderSelects(config);
    }
    function applyState(data, options = {}) {
      const config = data.config;
      providerTypes = data.provider_types || providerTypes;
      renderConfigIssue(data.config_issue);
      renderProviderTypeOptions();
      if (!options.preserveDraft) {
        applyConfig(config);
      } else {
        refreshProviderSelects({selected_provider: $("selected_provider").value});
      }

      const savedProviders = config.providers || [];
      const configured = config.has_rocom_api_key && savedProviders.some(provider => provider.enabled);
      $("configuredBadge").textContent = configured ? "已配置" : "未配置";
      $("configuredBadge").className = configured ? "badge ok" : "badge warn";
      const state = data.scheduler;
      $("runningBadge").textContent = state.running ? "调度中" : "未运行";
      $("busyBadge").textContent = state.in_progress ? "执行中" : "空闲";
      $("busyBadge").className = state.in_progress ? "badge warn" : "badge ok";
      $("nowBadge").textContent = prettyTime(data.now);
      $("logoutBtn").hidden = !data.auth_enabled;
      $("nextRun").textContent = prettyTime(state.next_run_at);
      $("lastStart").textContent = prettyTime(state.last_started_at);
      $("lastFinish").textContent = prettyTime(state.last_finished_at);
      $("lastCode").textContent = state.last_exit_code ?? "-";
      $("message").textContent = state.last_message || "-";
      renderPushResults(state.last_push_results || []);
      updateDraftBadge();
    }
    async function loadState(options = {}) {
      const data = await requestJSON("/api/state");
      applyState(data, options);
    }
    $("providers").addEventListener("click", async event => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      const index = Number(button.dataset.index);
      if (button.dataset.action === "remove") {
        providers.splice(index, 1);
        renderProviders();
        markConfigDirty();
      }
      if (button.dataset.action === "move-up" && index > 0) {
        providers = collectProviders();
        [providers[index - 1], providers[index]] = [providers[index], providers[index - 1]];
        renderProviders();
        markConfigDirty();
      }
      if (button.dataset.action === "move-down" && index < providers.length - 1) {
        providers = collectProviders();
        [providers[index + 1], providers[index]] = [providers[index], providers[index + 1]];
        renderProviders();
        markConfigDirty();
      }
      if (button.dataset.action === "test") {
        setBusy(true);
        try {
          const payload = buildConfigPayload();
          const provider = providers[index];
          const data = await requestJSON("/api/test-push", {
            method: "POST",
            body: JSON.stringify({provider_id: provider.id, config: payload}),
          });
          $("message").textContent = data.message;
        } catch (error) {
          $("message").textContent = error.message;
        } finally {
          setBusy(false);
        }
      }
    });
    $("addProviderBtn").addEventListener("click", () => {
      const type = $("newProviderType").value;
      const spec = providerTypes[type];
      if (!spec) {
        $("message").textContent = "通道类型还未加载完成，请稍后再试";
        return;
      }
      const config = {};
      (spec.fields || []).forEach(field => {
        if (field.default) config[field.name] = field.default;
      });
      providers.push({id: newId(type), type, name: spec.label, enabled: true, config});
      renderProviders();
      markConfigDirty();
    });
    async function saveConfig(showMessage = true) {
      const payload = buildConfigPayload();
      await requestJSON("/api/config", {method: "POST", body: JSON.stringify(payload)});
      clearConfigDirty();
      await loadState({preserveDraft: false});
      if (showMessage) $("message").textContent = "配置已保存";
    }
    $("configForm").addEventListener("input", event => {
      if (event.target && event.target.id !== "newProviderType") markConfigDirty();
    });
    $("configForm").addEventListener("change", event => {
      if (event.target && event.target.id !== "newProviderType") markConfigDirty();
    });
    $("configForm").addEventListener("submit", async event => {
      event.preventDefault();
      setBusy(true);
      try { await saveConfig(true); } catch (error) { $("message").textContent = error.message; } finally { setBusy(false); }
    });
    $("runBtn").addEventListener("click", async () => {
      if (configDirty) {
        $("message").textContent = "有未保存修改，请先保存配置再立即执行";
        updateDraftBadge();
        return;
      }
      setBusy(true);
      try {
        const data = await requestJSON("/api/run-now", {method: "POST", body: "{}"});
        $("message").textContent = data.message;
        await loadState({preserveDraft: configDirty});
      } catch (error) {
        $("message").textContent = error.message;
      } finally {
        setBusy(false);
      }
    });
    $("testBtn").addEventListener("click", async () => {
      setBusy(true);
      try {
        const data = await requestJSON("/api/test-push", {
          method: "POST",
          body: JSON.stringify({config: buildConfigPayload()}),
        });
        $("message").textContent = data.message;
      } catch (error) {
        $("message").textContent = error.message;
      } finally {
        setBusy(false);
      }
    });
    $("logoutBtn").addEventListener("click", async () => {
      try {
        await requestJSON("/api/logout", {method: "POST", body: "{}"});
      } finally {
        window.location.assign("/login");
      }
    });
    $("refreshBtn").addEventListener("click", () => loadState({preserveDraft: configDirty}));
    loadState().catch(error => $("message").textContent = error.message);
    setInterval(() => loadState({preserveDraft: configDirty}).catch(() => {}), 5000);
  </script>
</body>
</html>"""


if __name__ == "__main__":
    cli()
