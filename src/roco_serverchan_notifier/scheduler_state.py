from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from .settings import Settings


class SettingsStore(Protocol):
    def load(self) -> Settings: ...


@dataclass
class SchedulerState:
    running: bool = False
    in_progress: bool = False
    next_run_at: datetime | None = None
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    last_exit_code: int | None = None
    last_message: str = "尚未执行"
    last_push_results: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "running": self.running,
            "in_progress": self.in_progress,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_started_at": self.last_started_at.isoformat() if self.last_started_at else None,
            "last_finished_at": self.last_finished_at.isoformat() if self.last_finished_at else None,
            "last_exit_code": self.last_exit_code,
            "last_message": self.last_message,
            "last_push_results": self.last_push_results,
        }


class StaticSettingsStore:
    def __init__(self, settings: Settings):
        self._settings = settings

    def load(self) -> Settings:
        return self._settings
