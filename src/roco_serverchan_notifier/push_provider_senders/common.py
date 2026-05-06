from __future__ import annotations

from typing import Any

from ..provider_specs import provider_field_default
from ..push_models import ProviderConfig


def split_csv(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def provider_config_text(provider: ProviderConfig, field_name: str) -> str:
    value = provider.config.get(field_name)
    if value in (None, ""):
        value = provider_field_default(provider.type, field_name)
    return str(value or "").strip()
