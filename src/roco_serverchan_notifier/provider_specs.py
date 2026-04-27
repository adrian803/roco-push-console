from __future__ import annotations

from typing import Any


PROVIDER_TYPES: dict[str, dict[str, Any]] = {
    "serverchan": {
        "label": "Server 酱",
        "description": "通过 Server 酱 SendKey 推送到微信。",
        "fields": [
            {"name": "sendkey", "label": "SendKey", "secret": True, "required": True},
        ],
    },
    "pushplus": {
        "label": "PushPlus",
        "description": "通过 PushPlus token 推送，默认使用 markdown 模板。",
        "fields": [
            {"name": "token", "label": "Token", "secret": True, "required": True},
            {"name": "topic", "label": "群组编码", "required": False},
            {"name": "channel", "label": "渠道", "required": False},
        ],
    },
    "wecomchan": {
        "label": "Wecom 酱 / 企业微信应用",
        "description": "使用企业微信应用参数获取 access_token 后发送消息。",
        "fields": [
            {"name": "corpid", "label": "CorpID", "secret": True, "required": True},
            {"name": "secret", "label": "Secret", "secret": True, "required": True},
            {"name": "agentid", "label": "AgentID", "required": True},
            {"name": "touser", "label": "接收人", "required": True, "default": "@all"},
        ],
    },
    "wecom_bot": {
        "label": "企业微信群机器人",
        "description": "使用企业微信群机器人 webhook 或 key 推送 markdown。",
        "fields": [
            {"name": "webhook", "label": "Webhook", "secret": True, "required": False},
            {"name": "key", "label": "Key", "secret": True, "required": False},
        ],
    },
    "wxpusher": {
        "label": "WxPusher",
        "description": "通过 WxPusher appToken 推送给 UID 或主题。",
        "fields": [
            {"name": "app_token", "label": "AppToken", "secret": True, "required": True},
            {"name": "uids", "label": "UID 列表", "required": False},
            {"name": "topic_ids", "label": "Topic ID 列表", "required": False},
        ],
    },
    "bark": {
        "label": "Bark",
        "description": "通过 Bark server 和 device key 推送到 iOS。",
        "fields": [
            {"name": "server_url", "label": "Server URL", "required": True, "default": "https://api.day.app"},
            {"name": "device_key", "label": "Device Key", "secret": True, "required": True},
            {"name": "group", "label": "分组", "required": False, "default": "洛克王国"},
        ],
    },
    "dingtalk_bot": {
        "label": "钉钉群机器人",
        "description": "使用钉钉 webhook 推送 markdown，可选 secret 加签。",
        "fields": [
            {"name": "webhook", "label": "Webhook", "secret": True, "required": True},
            {"name": "secret", "label": "Secret", "secret": True, "required": False},
        ],
    },
    "feishu_bot": {
        "label": "飞书群机器人",
        "description": "使用飞书 webhook 推送富文本，可选 secret 加签。",
        "fields": [
            {"name": "webhook", "label": "Webhook", "secret": True, "required": True},
            {"name": "secret", "label": "Secret", "secret": True, "required": False},
        ],
    },
    "ntfy": {
        "label": "ntfy",
        "description": "发布到 ntfy topic，可选 bearer token。",
        "fields": [
            {"name": "base_url", "label": "Base URL", "required": True, "default": "https://ntfy.sh"},
            {"name": "topic", "label": "Topic", "secret": True, "required": True},
            {"name": "token", "label": "Token", "secret": True, "required": False},
            {"name": "priority", "label": "优先级", "required": False, "default": "default"},
            {"name": "tags", "label": "标签", "required": False},
        ],
    },
    "gotify": {
        "label": "Gotify",
        "description": "通过 Gotify app token 推送消息。",
        "fields": [
            {"name": "base_url", "label": "Base URL", "required": True},
            {"name": "app_token", "label": "App Token", "secret": True, "required": True},
            {"name": "priority", "label": "优先级", "required": False, "default": "5"},
        ],
    },
}


def provider_secret_fields(provider_type: str) -> set[str]:
    spec = PROVIDER_TYPES.get(provider_type, {})
    return {
        str(field["name"])
        for field in spec.get("fields", [])
        if field.get("secret")
    }


def provider_required_fields(provider_type: str) -> set[str]:
    spec = PROVIDER_TYPES.get(provider_type, {})
    return {
        str(field["name"])
        for field in spec.get("fields", [])
        if field.get("required")
    }

