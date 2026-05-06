from __future__ import annotations

import requests

from .provider_specs import provider_field_default, provider_required_fields
from .push_http import HttpSession
from .push_models import NotificationMessage, ProviderConfig, PushResult
from .push_provider_senders import (
    PROVIDER_SENDERS,
    send_bark,
    send_dingtalk_bot,
    send_feishu_bot,
    send_gotify,
    send_ntfy,
    send_pushplus,
    send_serverchan,
    send_wecom_bot,
    send_wecomchan,
    send_wxpusher,
    split_csv,
)
from .push_redaction import redact_sensitive_text


def _configured_or_default(provider: ProviderConfig, field_name: str) -> str:
    value = provider.config.get(field_name) or provider_field_default(provider.type, field_name)
    return str(value or "").strip()


def missing_required(provider: ProviderConfig) -> list[str]:
    return [
        field_name
        for field_name in provider_required_fields(provider.type)
        if not _configured_or_default(provider, field_name)
    ]


def send_provider(
    provider: ProviderConfig,
    message: NotificationMessage,
    *,
    session: HttpSession | None = None,
    timeout: int = 10,
) -> PushResult:
    missing = missing_required(provider)
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
            redact_sensitive_text(provider, result.message),
            result.status_code,
        )
    except Exception as exc:
        return PushResult(
            provider.id,
            provider.name,
            provider.type,
            False,
            redact_sensitive_text(provider, str(exc)),
        )
