from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from collections.abc import Awaitable, Callable
from datetime import datetime, time, timedelta

from .app import get_last_delivery_report, run
from .config import ConfigStore, DEFAULT_SCHEDULE_TIMES, Settings
from .time_utils import BEIJING_TZ, beijing_now, ensure_beijing_time


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


class SchedulerService:
    def __init__(self, store: ConfigStore):
        self.store = store
        self.state = SchedulerState()
        self._wake_event = asyncio.Event()
        self._run_lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    def wake(self) -> None:
        self._wake_event.set()

    async def run_now(self) -> bool:
        if self._run_lock.locked():
            return False
        asyncio.create_task(self._run_once("手动执行"))
        return True

    async def _run_once(self, reason: str) -> None:
        async with self._run_lock:
            settings = self.store.load()
            self.state.in_progress = True
            self.state.last_started_at = beijing_now()
            self.state.last_message = f"{reason}中"
            try:
                exit_code = await run(settings)
                self.state.last_exit_code = exit_code
                report = get_last_delivery_report()
                if report is not None:
                    self.state.last_push_results = report.to_dict()["results"]
                else:
                    self.state.last_push_results = []
                self.state.last_message = f"{reason}完成，状态码 {exit_code}"
            except Exception as exc:
                self.state.last_exit_code = 1
                self.state.last_message = f"{reason}异常: {exc}"
            finally:
                self.state.last_finished_at = beijing_now()
                self.state.in_progress = False

    async def _loop(self) -> None:
        self.state.running = True
        try:
            settings = self.store.load()
            if settings.run_on_start:
                await self._run_once("启动执行")

            while True:
                settings = self.store.load()
                try:
                    schedule_times = parse_schedule_times(settings.schedule_times)
                except ValueError as exc:
                    self.state.next_run_at = None
                    self.state.last_message = str(exc)
                    await self._wait_or_wake(60)
                    continue

                now = beijing_now()
                next_run = next_run_after(now, schedule_times)
                wait_seconds = max(0.0, (next_run - now).total_seconds())
                self.state.next_run_at = next_run
                print(
                    f"下一次执行: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}，"
                    f"等待 {int(wait_seconds)} 秒",
                    flush=True,
                )
                woke = await self._wait_or_wake(wait_seconds)
                if woke:
                    continue
                await self._run_once("定时执行")
        finally:
            self.state.running = False

    async def _wait_or_wake(self, timeout: float) -> bool:
        try:
            await asyncio.wait_for(self._wake_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return False
        self._wake_event.clear()
        return True


async def run_scheduler(
    settings: Settings,
    *,
    now_provider: Callable[[], datetime] = beijing_now,
    sleep_func: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    schedule_times = parse_schedule_times(settings.schedule_times)
    run_on_start = settings.run_on_start

    display_times = ", ".join(item.strftime("%H:%M") for item in schedule_times)
    print(f"容器调度器已启动，北京时间定时: {display_times}", flush=True)

    if run_on_start:
        print("RUN_ON_START=true，启动后立即执行一次", flush=True)
        await run(settings)

    while True:
        now = ensure_beijing_time(now_provider())
        next_run = next_run_after(now, schedule_times)
        wait_seconds = max(0.0, (next_run - now).total_seconds())
        print(
            f"下一次执行: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}，"
            f"等待 {int(wait_seconds)} 秒",
            flush=True,
        )
        await sleep_func(wait_seconds)

        started_at = ensure_beijing_time(now_provider())
        print(f"开始执行: {started_at.strftime('%Y-%m-%d %H:%M:%S %Z')}", flush=True)
        try:
            exit_code = await run(settings)
            print(f"本轮执行结束，状态码: {exit_code}", flush=True)
        except Exception as exc:
            print(f"本轮执行异常: {exc}", flush=True)


async def main() -> int:
    settings = ConfigStore().load()
    missing = settings.missing_required()
    if missing:
        print(f"缺少必要环境变量: {', '.join(missing)}", flush=True)
        return 2

    await run_scheduler(settings)
    return 0


def cli() -> None:
    raise SystemExit(asyncio.run(main()))


if __name__ == "__main__":
    cli()
