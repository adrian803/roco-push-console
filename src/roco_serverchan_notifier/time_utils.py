from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now() -> datetime:
    return datetime.now(BEIJING_TZ)


def ensure_beijing_time(value: datetime | None = None) -> datetime:
    if value is None:
        return beijing_now()
    if value.tzinfo is None:
        return value.replace(tzinfo=BEIJING_TZ)
    return value.astimezone(BEIJING_TZ)


def format_timestamp(ts_ms: Any) -> str:
    if not ts_ms:
        return "--:--"
    try:
        dt = datetime.fromtimestamp(int(ts_ms) / 1000, tz=BEIJING_TZ)
    except (TypeError, ValueError, OSError):
        return "--:--"
    return dt.strftime("%H:%M")


def get_round_info(now: datetime | None = None) -> dict[str, object]:
    now = ensure_beijing_time(now)
    start_time = now.replace(hour=8, minute=0, second=0, microsecond=0)

    if now < start_time:
        return {"current": "未开放", "total": 4, "countdown": "尚未开市"}

    delta_seconds = int((now - start_time).total_seconds())
    round_index = (delta_seconds // (4 * 3600)) + 1

    if round_index > 4:
        return {"current": 4, "total": 4, "countdown": "今日已收市"}

    round_end = start_time + timedelta(hours=round_index * 4)
    remaining = round_end - now
    hours, rem = divmod(max(0, int(remaining.total_seconds())), 3600)
    minutes, _ = divmod(rem, 60)
    countdown = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"

    return {"current": round_index, "total": 4, "countdown": countdown}

