from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .settings import Settings


DEFAULT_CONFIG_PATH = "/data/config.json"
PRESERVED_CONFIG_KEYS = {"console_auth"}


@dataclass(frozen=True)
class ConfigLoadIssue:
    message: str
    backup_path: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"message": self.message, "backup_path": self.backup_path}


class ConfigStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.environ.get("CONFIG_PATH", DEFAULT_CONFIG_PATH))
        self.last_load_issue: ConfigLoadIssue | None = None
        self._lock = threading.RLock()

    def load(self) -> Settings:
        with self._lock:
            base = Settings.from_env()
            payload = self._read_payload(record_issue=True)
            if payload is None:
                return base
            return Settings.from_mapping(payload, base=base)

    def save(self, settings: Settings) -> None:
        with self._lock:
            payload = settings.to_dict()
            payload.update(self._preserved_payload())
            self._write_payload(payload)

    def update(self, data: dict[str, Any]) -> Settings:
        with self._lock:
            settings = Settings.from_mapping(data, base=self.load(), keep_blank_secrets=True)
            self.save(settings)
            return settings

    def console_auth(self) -> dict[str, Any]:
        with self._lock:
            payload = self._read_payload(record_issue=True)
            if payload is None:
                return {}
            auth = payload.get("console_auth")
            return dict(auth) if isinstance(auth, dict) else {}

    def save_console_auth(self, auth: dict[str, Any]) -> None:
        with self._lock:
            payload = self._read_payload(record_issue=True) or {}
            payload["console_auth"] = dict(auth)
            self._write_payload(payload)

    def load_issue_dict(self) -> dict[str, str] | None:
        with self._lock:
            return self.last_load_issue.to_dict() if self.last_load_issue else None

    def _read_payload(self, *, record_issue: bool) -> dict[str, Any] | None:
        if not self.path.exists():
            return {}

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            if record_issue:
                self._record_load_issue(f"配置读取失败，已回退默认配置: {exc}")
            return None

        if not isinstance(payload, dict):
            if record_issue:
                self._record_load_issue("配置文件格式错误，已回退默认配置: 顶层不是 JSON 对象")
            return None

        if record_issue:
            self.last_load_issue = None
        return payload

    def _preserved_payload(self) -> dict[str, Any]:
        payload = self._read_payload(record_issue=False)
        if payload is None:
            return {}
        return {
            key: payload[key]
            for key in PRESERVED_CONFIG_KEYS
            if isinstance(payload.get(key), dict)
        }

    def _write_payload(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.path)
        self.last_load_issue = None

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
