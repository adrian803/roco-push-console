from __future__ import annotations

import base64
import hashlib
import hmac
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

import requests

from .provider_specs import PROVIDER_TYPES, provider_required_fields
from .provider_specs import provider_secret_fields

HttpSession = requests.Session


@dataclass(frozen=True)
class NotificationMessage:
    title: str
    body: str
    markdown: str


@dataclass(frozen=True)
class PushResult:
    provider_id: str
    provider_name: str
    provider_type: str
    success: bool
    message: str
    status_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_type": self.provider_type,
            "success": self.success,
            "message": self.message,
            "status_code": self.status_code,
        }


@dataclass(frozen=True)
class ProviderConfig:
    id: str
    type: str
    name: str
    enabled: bool
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ProviderConfig":
        provider_type = str(data.get("type", "serverchan")).strip()
        provider_id = str(data.get("id") or f"{provider_type}-{int(time.time() * 1000)}").strip()
        spec = PROVIDER_TYPES.get(provider_type, {})
        return cls(
            id=provider_id,
            type=provider_type,
            name=str(data.get("name") or spec.get("label") or provider_type).strip(),
            enabled=_to_bool(data.get("enabled"), True),
            config=dict(data.get("config") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "enabled": self.enabled,
            "config": dict(self.config),
        }


@dataclass(frozen=True)
class JsonPostRequest:
    provider: ProviderConfig
    session: HttpSession
    url: str
    payload: dict[str, Any]
    timeout: int
    headers: dict[str, str] | None = None
    success_codes: set[Any] = field(default_factory=lambda: {0, "0"})


@dataclass(frozen=True)
class DeliveryOptions:
    mode: str
    selected_provider: str = ""
    failover_order: list[str] | None = None
    session: HttpSession | None = None
    timeout: int = 10


def _to_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


def _split_csv(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _json_result(payload: dict[str, Any], success_codes: set[Any]) -> tuple[bool, str]:
    code = payload.get("code", payload.get("errcode"))
    success = code in success_codes
    if code is None and not payload:
        success = True
    message = str(payload.get("message") or payload.get("msg") or payload.get("errmsg") or payload)
    return success, message


def _missing_required(provider: ProviderConfig) -> list[str]:
    return [
        field_name
        for field_name in provider_required_fields(provider.type)
        if not str(provider.config.get(field_name, "")).strip()
    ]


_SENSITIVE_NAMES = "access_token|app_token|corpsecret|key|read_key|readkey|secret|sendkey|token|webhook"
_SENSITIVE_QUERY_RE = re.compile(rf"(?i)(\b(?:{_SENSITIVE_NAMES})=)([^&\s]+)")
_SENSITIVE_FIELD_RE = re.compile(
    rf"(?i)(['\"]?\b(?:{_SENSITIVE_NAMES})\b['\"]?\s*[:=]\s*['\"]?)"
    r"([^'\",\s}&]+)(['\"]?)"
)


def _redact_sensitive_text(provider: ProviderConfig, text: str) -> str:
    redacted = str(text)
    for field_name in provider_secret_fields(provider.type):
        value = str(provider.config.get(field_name) or "").strip()
        if value:
            redacted = redacted.replace(value, "[已脱敏]")
            redacted = redacted.replace(urllib.parse.quote_plus(value), "[已脱敏]")
            redacted = redacted.replace(urllib.parse.quote(value, safe=""), "[已脱敏]")
    redacted = _SENSITIVE_QUERY_RE.sub(r"\1[已脱敏]", redacted)
    return _SENSITIVE_FIELD_RE.sub(r"\1[已脱敏]\3", redacted)


def _result_from_response(
    provider: ProviderConfig,
    response: requests.Response,
    *,
    success_codes: set[Any],
) -> PushResult:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    success, message = _json_result(payload, success_codes)
    if response.status_code >= 400:
        success = False
        message = response.text[:200] or message
    return PushResult(
        provider.id,
        provider.name,
        provider.type,
        success,
        _redact_sensitive_text(provider, message),
        response.status_code,
    )


def _post_json(request: JsonPostRequest) -> PushResult:
    response = request.session.post(
        request.url,
        json=request.payload,
        headers=request.headers,
        timeout=request.timeout,
    )
    return _result_from_response(
        request.provider,
        response,
        success_codes=request.success_codes,
    )


def send_provider(
    provider: ProviderConfig,
    message: NotificationMessage,
    *,
    session: HttpSession | None = None,
    timeout: int = 10,
) -> PushResult:
    missing = _missing_required(provider)
    if missing:
        return PushResult(
            provider.id,
            provider.name,
            provider.type,
            False,
            f"缺少配置: {', '.join(missing)}",
        )

    client = session or requests.Session()
    try:
        sender = PROVIDER_SENDERS.get(provider.type)
        if sender is None:
            return PushResult(
                provider.id,
                provider.name,
                provider.type,
                False,
                f"未知通道类型: {provider.type}",
            )
        result = sender(provider, message, client, timeout)
        return PushResult(
            result.provider_id,
            result.provider_name,
            result.provider_type,
            result.success,
            _redact_sensitive_text(provider, result.message),
            result.status_code,
        )
    except Exception as exc:
        return PushResult(
            provider.id,
            provider.name,
            provider.type,
            False,
            _redact_sensitive_text(provider, str(exc)),
        )


def send_serverchan(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    url = f"https://sctapi.ftqq.com/{provider.config['sendkey']}.send"
    response = session.post(url, data={"title": message.title, "desp": message.markdown}, timeout=timeout)
    return _result_from_response(provider, response, success_codes={0, "0", None})


def send_pushplus(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    payload = {
        "token": provider.config["token"],
        "title": message.title,
        "content": message.markdown,
        "template": "markdown",
    }
    for key in ("topic", "channel"):
        value = str(provider.config.get(key, "")).strip()
        if value:
            payload[key] = value
    return _post_json(
        JsonPostRequest(
            provider,
            session,
            "https://www.pushplus.plus/send",
            payload,
            timeout,
            success_codes={200, "200", 0, "0"},
        )
    )


_WECOM_TOKEN_CACHE: dict[tuple[str, str], tuple[str, float]] = {}


def _get_wecom_token(provider: ProviderConfig, session: HttpSession, timeout: int) -> str:
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


def send_wecomchan(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    token = _get_wecom_token(provider, session, timeout)
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    payload = {
        "touser": provider.config.get("touser") or "@all",
        "msgtype": "text",
        "agentid": int(provider.config["agentid"]),
        "text": {"content": f"{message.title}\n\n{message.body}\n\n{message.markdown}"},
        "safe": 0,
    }
    return _post_json(JsonPostRequest(provider, session, url, payload, timeout))


def send_wecom_bot(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    webhook = str(provider.config.get("webhook") or "").strip()
    if not webhook:
        key = str(provider.config.get("key") or "").strip()
        if not key:
            return PushResult(provider.id, provider.name, provider.type, False, "缺少 webhook 或 key")
        webhook = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"
    payload = {"msgtype": "markdown", "markdown": {"content": message.markdown}}
    return _post_json(JsonPostRequest(provider, session, webhook, payload, timeout))


def send_wxpusher(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    payload: dict[str, Any] = {
        "appToken": provider.config["app_token"],
        "content": message.markdown,
        "summary": message.title,
        "contentType": 3,
    }
    uids = _split_csv(provider.config.get("uids"))
    topic_ids = _split_csv(provider.config.get("topic_ids"))
    if uids:
        payload["uids"] = uids
    if topic_ids:
        payload["topicIds"] = [int(item) if item.isdigit() else item for item in topic_ids]
    return _post_json(
        JsonPostRequest(
            provider,
            session,
            "https://wxpusher.zjiecode.com/api/send/message",
            payload,
            timeout,
            success_codes={1000, "1000", 0, "0"},
        )
    )


def send_bark(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    server_url = str(provider.config.get("server_url") or "https://api.day.app").rstrip("/")
    url = f"{server_url}/{provider.config['device_key']}"
    payload = {
        "title": message.title,
        "body": f"{message.body}\n\n{message.markdown}",
    }
    group = str(provider.config.get("group") or "").strip()
    if group:
        payload["group"] = group
    return _post_json(
        JsonPostRequest(
            provider,
            session,
            url,
            payload,
            timeout,
            success_codes={200, "200", 0, "0"},
        )
    )


def _append_dingtalk_sign(webhook: str, secret: str) -> str:
    if not secret:
        return webhook
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), string_to_sign, hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(digest))
    separator = "&" if "?" in webhook else "?"
    return f"{webhook}{separator}timestamp={timestamp}&sign={sign}"


def send_dingtalk_bot(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    webhook = _append_dingtalk_sign(provider.config["webhook"], str(provider.config.get("secret") or ""))
    payload = {
        "msgtype": "markdown",
        "markdown": {"title": message.title, "text": message.markdown},
    }
    return _post_json(JsonPostRequest(provider, session, webhook, payload, timeout))


def _feishu_sign(secret: str, timestamp: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(string_to_sign.encode("utf-8"), b"", digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def send_feishu_bot(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    payload: dict[str, Any] = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": message.title,
                    "content": [[{"tag": "text", "text": f"{message.body}\n\n{message.markdown}"}]],
                }
            }
        },
    }
    secret = str(provider.config.get("secret") or "").strip()
    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = _feishu_sign(secret, timestamp)
    return _post_json(
        JsonPostRequest(provider, session, provider.config["webhook"], payload, timeout)
    )


def send_ntfy(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    base_url = str(provider.config.get("base_url") or "https://ntfy.sh").rstrip("/")
    url = f"{base_url}/{provider.config['topic']}"
    headers = {
        "Title": message.title,
        "Markdown": "yes",
    }
    for name, header in (("priority", "Priority"), ("tags", "Tags")):
        value = str(provider.config.get(name) or "").strip()
        if value:
            headers[header] = value
    token = str(provider.config.get("token") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = session.post(
        url,
        data=message.markdown.encode("utf-8"),
        headers=headers,
        timeout=timeout,
    )
    success = 200 <= response.status_code < 300
    return PushResult(
        provider.id,
        provider.name,
        provider.type,
        success,
        response.text[:200] or response.reason,
        response.status_code,
    )


def send_gotify(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    base_url = str(provider.config["base_url"]).rstrip("/")
    app_token = urllib.parse.quote_plus(str(provider.config["app_token"]))
    url = f"{base_url}/message?token={app_token}"
    try:
        priority = int(provider.config.get("priority") or 5)
    except (TypeError, ValueError):
        priority = 5
    payload = {"title": message.title, "message": message.markdown, "priority": priority}
    response = session.post(url, json=payload, timeout=timeout)
    success = 200 <= response.status_code < 300
    message_text = response.text[:200] or response.reason
    return PushResult(provider.id, provider.name, provider.type, success, message_text, response.status_code)


PROVIDER_SENDERS = {
    "serverchan": send_serverchan,
    "pushplus": send_pushplus,
    "wecomchan": send_wecomchan,
    "wecom_bot": send_wecom_bot,
    "wxpusher": send_wxpusher,
    "bark": send_bark,
    "dingtalk_bot": send_dingtalk_bot,
    "feishu_bot": send_feishu_bot,
    "ntfy": send_ntfy,
    "gotify": send_gotify,
}


@dataclass(frozen=True)
class DeliveryReport:
    success: bool
    mode: str
    results: list[PushResult]

    def summary(self) -> str:
        if not self.results:
            return "没有可用推送通道"
        ok_count = sum(1 for item in self.results if item.success)
        return f"{ok_count}/{len(self.results)} 个通道成功"

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "mode": self.mode,
            "summary": self.summary(),
            "results": [item.to_dict() for item in self.results],
        }


def _delivery_options(
    options: DeliveryOptions | None,
    legacy_options: dict[str, Any],
) -> DeliveryOptions:
    if options is not None:
        if legacy_options:
            raise TypeError("options cannot be combined with legacy delivery keyword arguments")
        return options

    mode = str(legacy_options.pop("mode", "all"))
    selected_provider = str(legacy_options.pop("selected_provider", ""))
    failover_order = legacy_options.pop("failover_order", None)
    session = legacy_options.pop("session", None)
    timeout = int(legacy_options.pop("timeout", 10))
    if legacy_options:
        unexpected = ", ".join(sorted(legacy_options))
        raise TypeError(f"unexpected delivery option(s): {unexpected}")
    return DeliveryOptions(mode, selected_provider, failover_order, session, timeout)


def send_delivery(
    providers: list[ProviderConfig],
    message: NotificationMessage,
    *,
    options: DeliveryOptions | None = None,
    **legacy_options: Any,
) -> DeliveryReport:
    delivery_options = _delivery_options(options, legacy_options)
    client = delivery_options.session or requests.Session()
    enabled = [provider for provider in providers if provider.enabled]
    mode = delivery_options.mode
    if mode not in {"all", "single", "failover"}:
        mode = "all"

    if mode == "single":
        targets = [
            provider
            for provider in enabled
            if provider.id == delivery_options.selected_provider
        ]
    elif mode == "failover":
        order = delivery_options.failover_order or [provider.id for provider in enabled]
        provider_map = {provider.id: provider for provider in enabled}
        targets = [provider_map[item] for item in order if item in provider_map]
    else:
        targets = enabled

    results: list[PushResult] = []
    for provider in targets:
        result = send_provider(
            provider,
            message,
            session=client,
            timeout=delivery_options.timeout,
        )
        results.append(result)
        if mode == "failover" and result.success:
            break

    return DeliveryReport(any(result.success for result in results), mode, results)
