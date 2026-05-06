from __future__ import annotations

import os
from collections.abc import Collection
from typing import Any

from .provider_specs import (
    PROVIDER_TYPES,
    provider_env_fields,
    provider_env_id,
    provider_required_fields,
    provider_secret_fields,
)
from .push_models import ProviderConfig


def env_text(name: str) -> str:
    return os.environ.get(name, "").strip()


def env_text_or_default(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip() or default


def provider_order(providers: list[ProviderConfig]) -> list[str]:
    return [provider.id for provider in providers if provider.enabled]


def env_providers() -> list[ProviderConfig]:
    providers: list[ProviderConfig] = []
    for provider_type in PROVIDER_TYPES:
        provider = env_provider(provider_type)
        if provider:
            providers.append(provider)
    return providers


def env_provider(provider_type: str) -> ProviderConfig | None:
    spec = PROVIDER_TYPES.get(provider_type, {})
    config, has_explicit_value = env_provider_config(provider_type)
    required = provider_required_fields(provider_type)
    if not env_provider_is_complete(provider_type, config, has_explicit_value, required):
        return None

    return ProviderConfig(
        id=provider_env_id(provider_type),
        type=provider_type,
        name=str(spec.get("label") or provider_type),
        enabled=True,
        config=config,
    )


def env_provider_config(provider_type: str) -> tuple[dict[str, Any], bool]:
    spec = PROVIDER_TYPES.get(provider_type, {})
    field_envs = provider_env_fields(provider_type)
    config: dict[str, Any] = {}
    has_explicit_value = False

    for field in spec.get("fields", []):
        field_name = str(field["name"])
        value = env_text(field_envs.get(field_name, ""))
        if value:
            config[field_name] = value
            has_explicit_value = True
        elif "default" in field:
            config[field_name] = field["default"]

    return config, has_explicit_value


def env_provider_is_complete(
    provider_type: str, config: dict[str, Any], has_explicit_value: bool, required: Collection[str]
) -> bool:
    return has_explicit_value and all(str(config.get(name, "")).strip() for name in required)


def legacy_serverchan_provider(sendkey: str) -> ProviderConfig | None:
    sendkey = str(sendkey or "").strip()
    if not sendkey:
        return None
    spec = PROVIDER_TYPES.get("serverchan", {})
    return ProviderConfig(
        id=provider_env_id("serverchan"),
        type="serverchan",
        name=str(spec.get("label") or "serverchan"),
        enabled=True,
        config={"sendkey": sendkey},
    )


def parse_providers(
    data: dict[str, Any],
    *,
    base_providers: list[ProviderConfig],
    keep_blank_secrets: bool,
) -> list[ProviderConfig]:
    raw_providers = data.get("providers")
    if not isinstance(raw_providers, list):
        legacy = legacy_serverchan_provider(data.get("serverchan_sendkey"))
        if legacy:
            return [legacy]
        return list(base_providers)

    previous = {provider.id: provider for provider in base_providers}
    providers: list[ProviderConfig] = []
    for item in raw_providers:
        if not isinstance(item, dict):
            continue
        provider = ProviderConfig.from_mapping(item)
        old = previous.get(provider.id)
        config = {
            key: value
            for key, value in dict(provider.config).items()
            if not str(key).startswith("has_")
        }
        if keep_blank_secrets and old:
            for field_name in provider_secret_fields(provider.type):
                if str(config.get(field_name, "")).strip() == "":
                    old_value = old.config.get(field_name)
                    if old_value not in (None, ""):
                        config[field_name] = old_value

        for field in PROVIDER_TYPES.get(provider.type, {}).get("fields", []):
            field_name = str(field["name"])
            if field_name not in config and "default" in field:
                config[field_name] = field["default"]

        providers.append(
            ProviderConfig(
                id=provider.id,
                type=provider.type,
                name=provider.name,
                enabled=provider.enabled,
                config=config,
            )
        )
    return providers
