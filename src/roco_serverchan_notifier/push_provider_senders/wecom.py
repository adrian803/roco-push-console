from __future__ import annotations

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from ..push_provider_auth import get_wecom_token


def send_wecomchan(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    token = get_wecom_token(provider, session, timeout)
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    payload = {
        "touser": provider.config.get("touser") or "@all",
        "msgtype": "text",
        "agentid": int(provider.config["agentid"]),
        "text": {"content": f"{message.title}\n\n{message.body}\n\n{message.markdown}"},
        "safe": 0,
    }
    return post_json(JsonPostRequest(provider, session, url, payload, timeout))


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
    return post_json(JsonPostRequest(provider, session, webhook, payload, timeout))
