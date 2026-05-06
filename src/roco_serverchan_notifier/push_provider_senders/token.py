from __future__ import annotations

import urllib.parse
from typing import Any

from ..push_http import HttpSession, JsonPostRequest, post_json, result_from_response
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from .common import provider_config_text, split_csv


def send_serverchan(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    url = f"https://sctapi.ftqq.com/{provider.config['sendkey']}.send"
    response = session.post(url, data={"title": message.title, "desp": message.markdown}, timeout=timeout)
    return result_from_response(provider, response, success_codes={0, "0", None})


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
    return post_json(
        JsonPostRequest(
            provider,
            session,
            "https://www.pushplus.plus/send",
            payload,
            timeout,
            success_codes={200, "200", 0, "0"},
        )
    )


def send_wxpusher(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    payload: dict[str, Any] = {
        "appToken": provider.config["app_token"],
        "content": message.markdown,
        "summary": message.title,
        "contentType": 3,
    }
    uids = split_csv(provider.config.get("uids"))
    topic_ids = split_csv(provider.config.get("topic_ids"))
    if uids:
        payload["uids"] = uids
    if topic_ids:
        payload["topicIds"] = [int(item) if item.isdigit() else item for item in topic_ids]
    return post_json(
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
    server_url = provider_config_text(provider, "server_url").rstrip("/")
    url = f"{server_url}/{provider.config['device_key']}"
    payload = {
        "title": message.title,
        "body": f"{message.body}\n\n{message.markdown}",
    }
    group = provider_config_text(provider, "group")
    if group:
        payload["group"] = group
    return post_json(
        JsonPostRequest(
            provider,
            session,
            url,
            payload,
            timeout,
            success_codes={200, "200", 0, "0"},
        )
    )


def send_ntfy(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    base_url = provider_config_text(provider, "base_url").rstrip("/")
    url = f"{base_url}/{provider.config['topic']}"
    headers = {
        "Title": message.title,
        "Markdown": "yes",
    }
    for name, header in (("priority", "Priority"), ("tags", "Tags")):
        value = provider_config_text(provider, name)
        if value:
            headers[header] = value
    token = provider_config_text(provider, "token")
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
        priority = int(provider_config_text(provider, "priority") or 0)
    except (TypeError, ValueError):
        priority = 5
    if priority <= 0:
        priority = 5
    payload = {"title": message.title, "message": message.markdown, "priority": priority}
    response = session.post(url, json=payload, timeout=timeout)
    success = 200 <= response.status_code < 300
    message_text = response.text[:200] or response.reason
    return PushResult(provider.id, provider.name, provider.type, success, message_text, response.status_code)
