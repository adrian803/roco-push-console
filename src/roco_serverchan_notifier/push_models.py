from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .provider_specs import PROVIDER_TYPES


def _to_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


@dataclass(frozen=True)
class NotificationMessage:
    title: str
    body: str
    markdown: str


@dataclass(frozen=True)
class PushResult:
    provider_id: str
    provider_name: str
    provider_type: str
    success: bool
    message: str
    status_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_type": self.provider_type,
            "success": self.success,
            "message": self.message,
            "status_code": self.status_code,
        }


@dataclass(frozen=True)
class ProviderConfig:
    id: str
    type: str
    name: str
    enabled: bool
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ProviderConfig":
        provider_type = str(data.get("type", "serverchan")).strip()
        provider_id = str(data.get("id") or f"{provider_type}-{int(time.time() * 1000)}").strip()
        spec = PROVIDER_TYPES.get(provider_type, {})
        return cls(
            id=provider_id,
            type=provider_type,
            name=str(data.get("name") or spec.get("label") or provider_type).strip(),
            enabled=_to_bool(data.get("enabled"), True),
            config=dict(data.get("config") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "enabled": self.enabled,
            "config": dict(self.config),
        }


@dataclass(frozen=True)
class DeliveryOptions:
    mode: str
    selected_provider: str = ""
    failover_order: list[str] | None = None
    session: Any | None = None
    timeout: int = 10
