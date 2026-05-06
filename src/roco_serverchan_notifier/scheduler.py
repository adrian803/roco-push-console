from __future__ import annotations

import asyncio
from contextlib import suppress
from collections.abc import Awaitable, Callable
from datetime import datetime

from .app import RunResult, run
from .config_store import ConfigStore
from .schedule_policy import next_run_after, parse_schedule_times
from .scheduler_state import SchedulerState, SettingsStore, StaticSettingsStore
from .settings import Settings
from .time_utils import beijing_now, ensure_beijing_time


NowProvider = Callable[[], datetime]
SleepFunc = Callable[[float], Awaitable[None]]


class SchedulerService:
    def __init__(
        self,
        store: SettingsStore,
        *,
        now_provider: NowProvider = beijing_now,
        sleep_func: SleepFunc = asyncio.sleep,
    ):
        self.store = store
        self._now_provider = now_provider
        self._sleep = sleep_func
        self.state = SchedulerState()
        self._wake_event = asyncio.Event()
        self._run_lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._manual_run_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        task = self._task
        if task is not None and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        manual_task = self._manual_run_task
        if manual_task is not None and not manual_task.done():
            manual_task.cancel()
            with suppress(asyncio.CancelledError):
                await manual_task
        self._task = None
        self._manual_run_task = None
        self.state.running = False

    def wake(self) -> None:
        self._wake_event.set()

    async def run_now(self) -> bool:
        if self._run_lock.locked() or (
            self._manual_run_task is not None and not self._manual_run_task.done()
        ):
            return False
        task = asyncio.create_task(self._run_once("手动执行"))
        self._manual_run_task = task
        task.add_done_callback(self._clear_manual_run_task)
        return True

    def _clear_manual_run_task(self, task: asyncio.Task[None]) -> None:
        if self._manual_run_task is task:
            self._manual_run_task = None

    async def _run_once(self, reason: str) -> None:
        async with self._run_lock:
            settings = self.store.load()
            self.state.in_progress = True
            self.state.last_started_at = self._now()
            self.state.last_message = f"{reason}中"
            try:
                result = await run(settings)
                if isinstance(result, RunResult):
                    exit_code = result.exit_code
                    report = result.report
                else:
                    exit_code = int(result)
                    report = None
                self.state.last_exit_code = exit_code
                if report is not None:
                    self.state.last_push_results = report.to_dict()["results"]
                else:
                    self.state.last_push_results = []
                self.state.last_message = f"{reason}完成，状态码 {exit_code}"
            except Exception as exc:
                self.state.last_exit_code = 1
                self.state.last_message = f"{reason}异常: {exc}"
            finally:
                self.state.last_finished_at = self._now()
                self.state.in_progress = False

    async def serve_forever(self) -> None:
        await self._loop()

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

                now = self._now()
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
        if timeout <= 0:
            if self._wake_event.is_set():
                self._wake_event.clear()
                return True
            await self._sleep(0)
            return False

        wake_task = asyncio.create_task(self._wake_event.wait())
        sleep_task = asyncio.create_task(self._sleep(timeout))
        done, pending = await asyncio.wait(
            {wake_task, sleep_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

        woke = wake_task in done and wake_task.result()
        if woke:
            self._wake_event.clear()
        return woke

    def _now(self) -> datetime:
        return ensure_beijing_time(self._now_provider())


async def run_scheduler(
    settings: Settings,
    *,
    now_provider: NowProvider = beijing_now,
    sleep_func: SleepFunc = asyncio.sleep,
) -> None:
    schedule_times = parse_schedule_times(settings.schedule_times)
    display_times = ", ".join(item.strftime("%H:%M") for item in schedule_times)
    print(f"容器调度器已启动，北京时间定时: {display_times}", flush=True)
    service = SchedulerService(
        StaticSettingsStore(settings),
        now_provider=now_provider,
        sleep_func=sleep_func,
    )
    await service.serve_forever()


async def main() -> int:
    store = ConfigStore()
    settings = store.load()
    missing = settings.missing_required()
    if missing:
        print(f"缺少必要环境变量: {', '.join(missing)}", flush=True)
        return 2

    service = SchedulerService(store)
    await service.serve_forever()
    return 0


def cli() -> None:
    raise SystemExit(asyncio.run(main()))


if __name__ == "__main__":
    cli()
