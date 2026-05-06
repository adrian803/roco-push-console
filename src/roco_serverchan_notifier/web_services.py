from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import requests

from . import web_auth
from .config_store import ConfigStore
from .provider_specs import PROVIDER_TYPES, public_provider_types
from .push import send_delivery, send_provider
from .push_models import DeliveryOptions, NotificationMessage
from .scheduler import parse_schedule_times
from .settings import Settings
from .time_utils import beijing_now


def _format_dt(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else "-"


def build_state_payload(store: ConfigStore, scheduler: Any) -> dict[str, Any]:
    settings = store.load()
    return {
        "config": settings.public_dict(),
        "config_issue": store.load_issue_dict(),
        "provider_types": public_provider_types(),
        "scheduler": scheduler.state.to_dict(),
        "auth_enabled": web_auth.auth_enabled(store),
        "now": beijing_now().isoformat(),
    }


def validate_config_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("配置格式错误")

    schedule_times = str(payload.get("schedule_times", "")).strip()
    try:
        parse_schedule_times(schedule_times)
    except ValueError as exc:
        raise ValueError(f"定时格式错误: {exc}") from exc

    providers = payload.get("providers", [])
    if not isinstance(providers, list):
        raise ValueError("通道配置格式错误")
    for provider in providers:
        if not isinstance(provider, dict):
            raise ValueError("通道配置格式错误")
        if provider.get("type") not in PROVIDER_TYPES:
            raise ValueError(f"未知通道类型: {provider.get('type')}")

    return payload


def save_config_payload(store: ConfigStore, scheduler: Any, payload: Any) -> Settings:
    settings = store.update(validate_config_payload(payload))
    web_auth.reset_console_auth_cache()
    scheduler.wake()
    return settings


def settings_from_test_payload(store: ConfigStore, payload: Any) -> Settings:
    settings = store.load()
    if not isinstance(payload, dict):
        return settings

    draft_config = payload.get("config")
    if not isinstance(draft_config, dict):
        return settings

    for provider in draft_config.get("providers", []):
        if not isinstance(provider, dict) or provider.get("type") not in PROVIDER_TYPES:
            provider_type = provider.get("type") if isinstance(provider, dict) else provider
            raise ValueError(f"未知通道类型: {provider_type}")

    return Settings.from_mapping(draft_config, base=settings, keep_blank_secrets=True)


def _test_message() -> NotificationMessage:
    return NotificationMessage(
        "远行商人提醒测试",
        "控制台测试推送成功。",
        f"### 控制台测试推送\n\n北京时间：{_format_dt(beijing_now())}",
    )


async def send_test_push(
    store: ConfigStore,
    payload: Any,
    *,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    provider_id = str(payload.get("provider_id", "")).strip() if isinstance(payload, dict) else ""
    settings = settings_from_test_payload(store, payload)
    message = _test_message()
    session = session or requests.Session()

    if provider_id:
        provider = next((item for item in settings.providers if item.id == provider_id), None)
        if provider is None:
            raise LookupError("通道不存在")
        result = await asyncio.to_thread(
            send_provider,
            provider,
            message,
            session=session,
            timeout=settings.http_timeout,
        )
        if not result.success:
            raise RuntimeError(f"测试推送失败: {result.message}")
        return {"ok": True, "message": f"{provider.name} 测试推送已发送", "results": [result.to_dict()]}

    report = await asyncio.to_thread(
        send_delivery,
        settings.providers,
        message,
        options=DeliveryOptions(
            mode=settings.delivery_mode,
            selected_provider=settings.selected_provider,
            failover_order=settings.failover_order,
            session=session,
            timeout=settings.http_timeout,
        ),
    )
    if not report.success:
        raise RuntimeError(f"测试推送失败: {report.summary()}")
    return {"ok": True, "message": "测试推送已发送", "results": report.to_dict()["results"]}
