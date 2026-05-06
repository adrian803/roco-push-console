from __future__ import annotations

import time

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from ..push_provider_auth import append_dingtalk_sign, feishu_sign


def send_dingtalk_bot(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    webhook = append_dingtalk_sign(provider.config["webhook"], str(provider.config.get("secret") or ""))
    payload = {
        "msgtype": "markdown",
        "markdown": {"title": message.title, "text": message.markdown},
    }
    return post_json(JsonPostRequest(provider, session, webhook, payload, timeout))


def send_feishu_bot(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    payload: dict[str, object] = {
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
        payload["sign"] = feishu_sign(secret, timestamp)
    return post_json(
        JsonPostRequest(provider, session, provider.config["webhook"], payload, timeout)
    )
