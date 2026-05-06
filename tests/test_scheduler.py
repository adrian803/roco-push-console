from __future__ import annotations

import asyncio
import importlib
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

try:
    from .helpers import RocoTestCase
except ImportError:
    from helpers import RocoTestCase

from roco_serverchan_notifier import app as app_module
from roco_serverchan_notifier.config import ConfigStore
from roco_serverchan_notifier.push import DeliveryReport, PushResult
from roco_serverchan_notifier.scheduler import SchedulerService, SchedulerState, next_run_after, parse_schedule_times



class SchedulerTests(RocoTestCase):
    def test_scheduler_delegates_policy_and_state_modules(self):
        policy = importlib.import_module("roco_serverchan_notifier.schedule_policy")
        state = importlib.import_module("roco_serverchan_notifier.scheduler_state")

        self.assertIs(parse_schedule_times, policy.parse_schedule_times)
        self.assertIs(next_run_after, policy.next_run_after)
        self.assertIs(SchedulerState, state.SchedulerState)

    def test_parse_schedule_times_sorts_times(self):
        times = parse_schedule_times("20:01,08:01,12:01")

        self.assertEqual([item.strftime("%H:%M") for item in times], ["08:01", "12:01", "20:01"])

    def test_default_schedule_times_are_five_minutes_after_refresh(self):
        times = parse_schedule_times(None)

        self.assertEqual(
            [item.strftime("%H:%M") for item in times],
            ["08:05", "12:05", "16:05", "20:05"],
        )

    def test_next_run_after_rolls_to_tomorrow(self):
        tz = timezone(timedelta(hours=8))
        now = datetime(2026, 4, 26, 21, 0, tzinfo=tz)
        times = parse_schedule_times("08:01,12:01")

        next_run = next_run_after(now, times)

        self.assertEqual(next_run, datetime(2026, 4, 27, 8, 1, tzinfo=tz))

    def test_scheduler_clears_stale_push_results_when_no_report(self):
        async def exercise():
            with tempfile.TemporaryDirectory() as temp_dir:
                store = ConfigStore(Path(temp_dir) / "config.json")
                store.save(self.make_settings())
                scheduler = SchedulerService(store)
                scheduler.state.last_push_results = [{"provider_name": "旧结果"}]
                with patch(
                    "roco_serverchan_notifier.scheduler.run",
                    new=AsyncMock(return_value=app_module.RunResult(0)),
                ):
                    await scheduler._run_once("测试执行")
                return scheduler.state.last_push_results

        self.assertEqual(asyncio.run(exercise()), [])

    def test_scheduler_uses_run_result_report(self):
        async def exercise():
            with tempfile.TemporaryDirectory() as temp_dir:
                store = ConfigStore(Path(temp_dir) / "config.json")
                store.save(self.make_settings())
                scheduler = SchedulerService(store)
                report = DeliveryReport(True, "all", [PushResult("p1", "通道", "serverchan", True, "ok")])
                run_result = app_module.RunResult(exit_code=0, report=report)
                with patch("roco_serverchan_notifier.scheduler.run", new=AsyncMock(return_value=run_result)):
                    await scheduler._run_once("测试执行")
                return scheduler.state.last_push_results

        self.assertEqual(asyncio.run(exercise())[0]["provider_id"], "p1")

    def test_run_now_rejects_duplicate_manual_run_before_task_acquires_lock(self):
        async def exercise():
            with tempfile.TemporaryDirectory() as temp_dir:
                store = ConfigStore(Path(temp_dir) / "config.json")
                store.save(self.make_settings())
                scheduler = SchedulerService(store)
                release = asyncio.Event()
                started = 0

                async def slow_run(settings):
                    nonlocal started
                    started += 1
                    await release.wait()
                    return app_module.RunResult(0)

                with patch("roco_serverchan_notifier.scheduler.run", new=slow_run):
                    first = await scheduler.run_now()
                    second = await scheduler.run_now()
                    await asyncio.sleep(0)
                    release.set()
                    await asyncio.sleep(0.05)
                    return first, second, started

        self.assertEqual(asyncio.run(exercise()), (True, False, 1))


if __name__ == "__main__":
    unittest.main()
