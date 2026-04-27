from __future__ import annotations

import os

from . import app, scheduler, web
from .config import ConfigStore


MODE_ALIASES = {
    "": "auto",
    "auto": "auto",
    "web": "web",
    "console": "web",
    "ui": "web",
    "scheduler": "scheduler",
    "schedule": "scheduler",
    "headless": "scheduler",
    "cron": "scheduler",
    "managed": "scheduler",
    "daemon": "scheduler",
    "no-web": "scheduler",
    "no-ui": "scheduler",
    "once": "once",
    "run-once": "once",
}


def normalize_app_mode(value: str | None) -> str:
    mode = str(value or "").strip().lower()
    if mode in MODE_ALIASES:
        return MODE_ALIASES[mode]
    valid = ", ".join(sorted({item for item in MODE_ALIASES.values()}))
    raise SystemExit(f"未知 APP_MODE: {value!r}，可用模式: {valid}")


def resolve_app_mode(value: str | None = None) -> str:
    mode = normalize_app_mode(value if value is not None else os.environ.get("APP_MODE"))
    if mode != "auto":
        return mode

    settings = ConfigStore().load()
    return "web" if settings.missing_required() else "scheduler"


def main() -> None:
    mode = resolve_app_mode()
    if mode == "scheduler":
        return scheduler.cli()
    if mode == "once":
        return app.cli()
    return web.cli()


if __name__ == "__main__":
    main()
