from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from .env_providers import env_providers, env_text_or_default, parse_providers, provider_order
from .provider_specs import provider_secret_fields
from .push_models import ProviderConfig


DEFAULT_GAME_API_URL = (
    "https://wegame.shallow.ink/api/v1/games/rocom/merchant/info"
)
DEFAULT_SCHEDULE_TIMES = "08:05,12:05,16:05,20:05"


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


def public_provider(provider: ProviderConfig) -> dict[str, Any]:
    data = provider.to_dict()
    config = dict(data["config"])
    for field_name in provider_secret_fields(provider.type):
        value = config.get(field_name)
        config[field_name] = ""
        config[f"has_{field_name}"] = bool(value)
    data["config"] = config
    return data


@dataclass(frozen=True)
class Settings:
    rocom_api_key: str
    game_api_url: str
    notify_empty: bool
    http_timeout: int
    schedule_times: str
    run_on_start: bool
    delivery_mode: str
    selected_provider: str
    failover_order: list[str]
    providers: list[ProviderConfig]
    include_price_info: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        providers = env_providers()
        default_provider_id = providers[0].id if providers else ""
        return cls(
            rocom_api_key=os.environ.get("ROCOM_API_KEY", "").strip(),
            game_api_url=env_text_or_default("ROCOM_API_URL", DEFAULT_GAME_API_URL),
            notify_empty=env_bool("NOTIFY_EMPTY", False),
            http_timeout=env_int("HTTP_TIMEOUT", 30),
            schedule_times=env_text_or_default("SCHEDULE_TIMES", DEFAULT_SCHEDULE_TIMES),
            run_on_start=env_bool("RUN_ON_START", False),
            include_price_info=env_bool("INCLUDE_PRICE_INFO", False),
            delivery_mode=os.environ.get("DELIVERY_MODE", "all").strip() or "all",
            selected_provider=os.environ.get("SELECTED_PROVIDER", "").strip() or default_provider_id,
            failover_order=provider_order(providers),
            providers=providers,
        )

    @classmethod
    def from_mapping(
        cls,
        data: dict[str, Any],
        *,
        base: "Settings | None" = None,
        keep_blank_secrets: bool = False,
    ) -> "Settings":
        base = base or cls.from_env()

        def text(name: str, current: str) -> str:
            value = data.get(name, current)
            if value is None:
                return current
            value = str(value).strip()
            if keep_blank_secrets and name in {"rocom_api_key"} and not value:
                return current
            return value

        try:
            http_timeout = int(data.get("http_timeout", base.http_timeout) or 30)
        except (TypeError, ValueError):
            http_timeout = base.http_timeout

        providers = parse_providers(
            data,
            base_providers=base.providers,
            keep_blank_secrets=keep_blank_secrets,
        )
        delivery_mode = text("delivery_mode", base.delivery_mode)
        if delivery_mode not in {"all", "single", "failover"}:
            delivery_mode = "all"
        provider_ids = {provider.id for provider in providers if provider.enabled}
        selected_provider = text("selected_provider", base.selected_provider)
        if selected_provider not in provider_ids:
            selected_provider = next(iter(provider_order(providers)), "")

        return cls(
            rocom_api_key=text("rocom_api_key", base.rocom_api_key),
            game_api_url=text("game_api_url", base.game_api_url) or DEFAULT_GAME_API_URL,
            notify_empty=coerce_bool(data.get("notify_empty"), base.notify_empty),
            http_timeout=max(1, http_timeout),
            schedule_times=text("schedule_times", base.schedule_times) or DEFAULT_SCHEDULE_TIMES,
            run_on_start=coerce_bool(data.get("run_on_start"), base.run_on_start),
            include_price_info=coerce_bool(data.get("include_price_info"), base.include_price_info),
            delivery_mode=delivery_mode,
            selected_provider=selected_provider,
            failover_order=provider_order(providers),
            providers=providers,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rocom_api_key": self.rocom_api_key,
            "game_api_url": self.game_api_url,
            "notify_empty": self.notify_empty,
            "http_timeout": self.http_timeout,
            "schedule_times": self.schedule_times,
            "run_on_start": self.run_on_start,
            "include_price_info": self.include_price_info,
            "delivery_mode": self.delivery_mode,
            "selected_provider": self.selected_provider,
            "failover_order": list(self.failover_order),
            "providers": [provider.to_dict() for provider in self.providers],
        }

    def public_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        data["rocom_api_key"] = ""
        data["has_rocom_api_key"] = bool(self.rocom_api_key)
        data["providers"] = [public_provider(provider) for provider in self.providers]
        return data

    def missing_required(self) -> list[str]:
        missing: list[str] = []
        if not self.rocom_api_key:
            missing.append("ROCOM_API_KEY")
        if not any(provider.enabled for provider in self.providers):
            missing.append("PUSH_PROVIDER")
        return missing
