from __future__ import annotations

import os
import json
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .provider_specs import PROVIDER_TYPES, provider_secret_fields
from .push import ProviderConfig


DEFAULT_GAME_API_URL = (
    "https://wegame.shallow.ink/api/v1/games/rocom/merchant/info?refresh=true"
)
DEFAULT_SCHEDULE_TIMES = "08:05,12:05,16:05,20:05"
DEFAULT_CONFIG_PATH = "/data/config.json"

ENV_PROVIDER_FIELDS: dict[str, dict[str, str]] = {
    "serverchan": {"sendkey": "SERVERCHAN_SENDKEY"},
    "pushplus": {
        "token": "PUSHPLUS_TOKEN",
        "topic": "PUSHPLUS_TOPIC",
        "channel": "PUSHPLUS_CHANNEL",
    },
    "wecomchan": {
        "corpid": "WECOM_CORPID",
        "secret": "WECOM_SECRET",
        "agentid": "WECOM_AGENTID",
        "touser": "WECOM_TOUSER",
    },
    "wecom_bot": {"webhook": "WECOM_BOT_WEBHOOK", "key": "WECOM_BOT_KEY"},
    "wxpusher": {
        "app_token": "WXPUSHER_APP_TOKEN",
        "uids": "WXPUSHER_UIDS",
        "topic_ids": "WXPUSHER_TOPIC_IDS",
    },
    "bark": {
        "server_url": "BARK_SERVER_URL",
        "device_key": "BARK_DEVICE_KEY",
        "group": "BARK_GROUP",
    },
    "dingtalk_bot": {"webhook": "DINGTALK_WEBHOOK", "secret": "DINGTALK_SECRET"},
    "feishu_bot": {"webhook": "FEISHU_WEBHOOK", "secret": "FEISHU_SECRET"},
    "ntfy": {
        "base_url": "NTFY_BASE_URL",
        "topic": "NTFY_TOPIC",
        "token": "NTFY_TOKEN",
        "priority": "NTFY_PRIORITY",
        "tags": "NTFY_TAGS",
    },
    "gotify": {
        "base_url": "GOTIFY_BASE_URL",
        "app_token": "GOTIFY_APP_TOKEN",
        "priority": "GOTIFY_PRIORITY",
    },
}

ENV_PROVIDER_IDS = {
    "serverchan": "serverchan-default",
    "pushplus": "pushplus-env",
    "wecomchan": "wecomchan-env",
    "wecom_bot": "wecom-bot-env",
    "wxpusher": "wxpusher-env",
    "bark": "bark-env",
    "dingtalk_bot": "dingtalk-env",
    "feishu_bot": "feishu-env",
    "ntfy": "ntfy-env",
    "gotify": "gotify-env",
}


@dataclass(frozen=True)
class ConfigLoadIssue:
    message: str
    backup_path: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"message": self.message, "backup_path": self.backup_path}


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _to_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


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

    @classmethod
    def from_env(cls) -> "Settings":
        providers = _env_providers()
        default_provider_id = providers[0].id if providers else ""
        return cls(
            rocom_api_key=os.environ.get("ROCOM_API_KEY", "").strip(),
            game_api_url=_env_text_or_default("ROCOM_API_URL", DEFAULT_GAME_API_URL),
            notify_empty=_env_bool("NOTIFY_EMPTY", False),
            http_timeout=_env_int("HTTP_TIMEOUT", 30),
            schedule_times=_env_text_or_default("SCHEDULE_TIMES", DEFAULT_SCHEDULE_TIMES),
            run_on_start=_env_bool("RUN_ON_START", False),
            delivery_mode=os.environ.get("DELIVERY_MODE", "all").strip() or "all",
            selected_provider=os.environ.get("SELECTED_PROVIDER", "").strip() or default_provider_id,
            failover_order=_provider_order(providers),
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

        providers = _parse_providers(data, base=base, keep_blank_secrets=keep_blank_secrets)
        delivery_mode = text("delivery_mode", base.delivery_mode)
        if delivery_mode not in {"all", "single", "failover"}:
            delivery_mode = "all"
        provider_ids = {provider.id for provider in providers if provider.enabled}
        selected_provider = text("selected_provider", base.selected_provider)
        if selected_provider not in provider_ids:
            selected_provider = next(iter(_provider_order(providers)), "")

        return cls(
            rocom_api_key=text("rocom_api_key", base.rocom_api_key),
            game_api_url=text("game_api_url", base.game_api_url) or DEFAULT_GAME_API_URL,
            notify_empty=_to_bool(data.get("notify_empty"), base.notify_empty),
            http_timeout=max(1, http_timeout),
            schedule_times=text("schedule_times", base.schedule_times) or DEFAULT_SCHEDULE_TIMES,
            run_on_start=_to_bool(data.get("run_on_start"), base.run_on_start),
            delivery_mode=delivery_mode,
            selected_provider=selected_provider,
            failover_order=_provider_order(providers),
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
            "delivery_mode": self.delivery_mode,
            "selected_provider": self.selected_provider,
            "failover_order": list(self.failover_order),
            "providers": [provider.to_dict() for provider in self.providers],
        }

    def public_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        data["rocom_api_key"] = ""
        data["has_rocom_api_key"] = bool(self.rocom_api_key)
        data["providers"] = [_public_provider(provider) for provider in self.providers]
        return data

    def missing_required(self) -> list[str]:
        missing: list[str] = []
        if not self.rocom_api_key:
            missing.append("ROCOM_API_KEY")
        if not any(provider.enabled for provider in self.providers):
            missing.append("PUSH_PROVIDER")
        return missing


class ConfigStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.environ.get("CONFIG_PATH", DEFAULT_CONFIG_PATH))
        self.last_load_issue: ConfigLoadIssue | None = None
        self._lock = threading.RLock()

    def load(self) -> Settings:
        with self._lock:
            base = Settings.from_env()
            if not self.path.exists():
                return base

            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self._record_load_issue(f"配置读取失败，已回退默认配置: {exc}")
                return base

            if not isinstance(payload, dict):
                self._record_load_issue("配置文件格式错误，已回退默认配置: 顶层不是 JSON 对象")
                return base
            self.last_load_issue = None
            return Settings.from_mapping(payload, base=base)

    def save(self, settings: Settings) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            temp_path.write_text(
                json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_path.replace(self.path)
            self.last_load_issue = None

    def update(self, data: dict[str, Any]) -> Settings:
        with self._lock:
            settings = Settings.from_mapping(data, base=self.load(), keep_blank_secrets=True)
            self.save(settings)
            return settings

    def load_issue_dict(self) -> dict[str, str] | None:
        with self._lock:
            return self.last_load_issue.to_dict() if self.last_load_issue else None

    def _record_load_issue(self, message: str) -> None:
        backup_path, backup_error = self._backup_invalid_config()
        if backup_path:
            message = f"{message}；原文件已备份到 {backup_path}"
        elif backup_error:
            message = f"{message}；原文件备份失败: {backup_error}"
        self.last_load_issue = ConfigLoadIssue(message=message, backup_path=backup_path)

    def _backup_invalid_config(self) -> tuple[str, str]:
        if not self.path.exists():
            return "", ""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = self.path.with_name(f"{self.path.name}.invalid-{timestamp}.bak")
        try:
            self.path.replace(backup_path)
        except OSError as exc:
            return "", str(exc)
        return str(backup_path), ""


def _provider_order(providers: list[ProviderConfig]) -> list[str]:
    return [provider.id for provider in providers if provider.enabled]


def _env_text(name: str) -> str:
    return os.environ.get(name, "").strip()


def _env_text_or_default(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip() or default


def _env_providers() -> list[ProviderConfig]:
    providers: list[ProviderConfig] = []
    for provider_type in ENV_PROVIDER_FIELDS:
        provider = _env_provider(provider_type)
        if provider:
            providers.append(provider)
    return providers


def _env_provider(provider_type: str) -> ProviderConfig | None:
    spec = PROVIDER_TYPES.get(provider_type, {})
    config, has_explicit_value = _env_provider_config(provider_type, spec)
    required = _provider_required_fields(spec)
    if not _env_provider_is_complete(provider_type, config, has_explicit_value, required):
        return None

    return ProviderConfig(
        id=ENV_PROVIDER_IDS[provider_type],
        type=provider_type,
        name=str(spec.get("label") or provider_type),
        enabled=True,
        config=config,
    )


def _env_provider_config(provider_type: str, spec: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    field_envs = ENV_PROVIDER_FIELDS[provider_type]
    config: dict[str, Any] = {}
    has_explicit_value = False

    for field in spec.get("fields", []):
        field_name = str(field["name"])
        value = _env_text(field_envs.get(field_name, ""))
        if value:
            config[field_name] = value
            has_explicit_value = True
        elif "default" in field:
            config[field_name] = field["default"]

    return config, has_explicit_value


def _provider_required_fields(spec: dict[str, Any]) -> list[str]:
    return [
        str(field["name"])
        for field in spec.get("fields", [])
        if field.get("required")
    ]


def _env_provider_is_complete(
    provider_type: str, config: dict[str, Any], has_explicit_value: bool, required: list[str]
) -> bool:
    if provider_type == "wecom_bot":
        return bool(config.get("webhook") or config.get("key"))

    return has_explicit_value and all(str(config.get(name, "")).strip() for name in required)


def _legacy_serverchan_provider(sendkey: str) -> ProviderConfig | None:
    sendkey = str(sendkey or "").strip()
    if not sendkey:
        return None
    return ProviderConfig(
        id="serverchan-default",
        type="serverchan",
        name="Server 酱",
        enabled=True,
        config={"sendkey": sendkey},
    )


def _parse_providers(
    data: dict[str, Any],
    *,
    base: Settings,
    keep_blank_secrets: bool,
) -> list[ProviderConfig]:
    raw_providers = data.get("providers")
    if not isinstance(raw_providers, list):
        legacy = _legacy_serverchan_provider(data.get("serverchan_sendkey"))
        if legacy:
            return [legacy]
        return list(base.providers)

    previous = {provider.id: provider for provider in base.providers}
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


def _public_provider(provider: ProviderConfig) -> dict[str, Any]:
    data = provider.to_dict()
    config = dict(data["config"])
    for field_name in provider_secret_fields(provider.type):
        value = config.get(field_name)
        config[field_name] = ""
        config[f"has_{field_name}"] = bool(value)
    data["config"] = config
    return data
