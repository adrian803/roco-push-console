from __future__ import annotations

from datetime import datetime, time, timedelta

from .settings import DEFAULT_SCHEDULE_TIMES
from .time_utils import BEIJING_TZ, ensure_beijing_time


def parse_schedule_times(value: str | None) -> list[time]:
    raw_value = (value or DEFAULT_SCHEDULE_TIMES).strip()
    result: list[time] = []
    for part in raw_value.split(","):
        text = part.strip()
        if not text:
            continue
        try:
            hour_text, minute_text = text.split(":", 1)
            hour = int(hour_text)
            minute = int(minute_text)
        except ValueError as exc:
            raise ValueError(f"无效的定时时间: {text}") from exc

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"无效的定时时间: {text}")
        result.append(time(hour=hour, minute=minute, tzinfo=BEIJING_TZ))

    if not result:
        raise ValueError("SCHEDULE_TIMES 至少需要配置一个时间")
    return sorted(result)


def next_run_after(now: datetime, schedule_times: list[time]) -> datetime:
    now = ensure_beijing_time(now)
    today = now.date()

    for schedule_time in schedule_times:
        candidate = datetime.combine(today, schedule_time)
        if candidate > now:
            return candidate

    return datetime.combine(today + timedelta(days=1), schedule_times[0])
