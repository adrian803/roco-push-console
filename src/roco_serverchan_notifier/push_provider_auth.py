from __future__ import annotations

import base64
import hashlib
import hmac
import time
import urllib.parse

import requests

from .push_models import ProviderConfig

HttpSession = requests.Session

_WECOM_TOKEN_CACHE: dict[tuple[str, str], tuple[str, float]] = {}


def get_wecom_token(provider: ProviderConfig, session: HttpSession, timeout: int) -> str:
    corpid = provider.config["corpid"]
    secret = provider.config["secret"]
    cache_key = (corpid, secret)
    cached = _WECOM_TOKEN_CACHE.get(cache_key)
    now = time.time()
    if cached and cached[1] > now + 60:
        return cached[0]

    response = session.get(
        "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
        params={"corpid": corpid, "corpsecret": secret},
        timeout=timeout,
    )
    payload = response.json()
    if response.status_code >= 400 or payload.get("errcode") not in (0, "0"):
        raise RuntimeError(str(payload.get("errmsg") or payload))
    token = str(payload["access_token"])
    expires_in = int(payload.get("expires_in", 7200))
    _WECOM_TOKEN_CACHE[cache_key] = (token, now + expires_in)
    return token


def append_dingtalk_sign(webhook: str, secret: str) -> str:
    if not secret:
        return webhook
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), string_to_sign, hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(digest))
    separator = "&" if "?" in webhook else "?"
    return f"{webhook}{separator}timestamp={timestamp}&sign={sign}"


def feishu_sign(secret: str, timestamp: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(string_to_sign.encode("utf-8"), b"", digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")
