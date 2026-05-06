from __future__ import annotations

from typing import Any

import requests

from .push_delivery import DeliveryContext, DeliveryReport, send_delivery_with_options
from .push_http import HttpSession, JsonPostRequest
from .push_models import DeliveryOptions, NotificationMessage, ProviderConfig, PushResult
from .push_provider_auth import (
    _WECOM_TOKEN_CACHE,
    append_dingtalk_sign,
    feishu_sign,
    get_wecom_token,
)
from .push_providers import (
    PROVIDER_SENDERS,
    missing_required,
    send_bark,
    send_dingtalk_bot,
    send_feishu_bot,
    send_gotify,
    send_ntfy,
    send_provider as _send_provider_impl,
    send_pushplus,
    send_serverchan,
    send_wecom_bot,
    send_wecomchan,
    send_wxpusher,
    split_csv,
)


def _get_wecom_token(provider: ProviderConfig, session: HttpSession, timeout: int) -> str:
    return get_wecom_token(provider, session, timeout)


def _append_dingtalk_sign(webhook: str, secret: str) -> str:
    return append_dingtalk_sign(webhook, secret)


def _feishu_sign(secret: str, timestamp: str) -> str:
    return feishu_sign(secret, timestamp)


def _split_csv(value: Any) -> list[str]:
    return split_csv(value)


def _missing_required(provider: ProviderConfig) -> list[str]:
    return missing_required(provider)


def send_provider(
    provider: ProviderConfig,
    message: NotificationMessage,
    *,
    session: HttpSession | None = None,
    timeout: int = 10,
) -> PushResult:
    return _send_provider_impl(
        provider,
        message,
        session=session,
        timeout=timeout,
    )


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
    return send_delivery_with_options(
        providers,
        delivery_options,
        DeliveryContext(
            message=message,
            sender=send_provider,
            session_factory=requests.Session,
            timeout=delivery_options.timeout,
        ),
    )
