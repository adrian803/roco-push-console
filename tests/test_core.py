from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from roco_push_console import app as app_module
from roco_push_console import web as web_module
from roco_push_console.app import build_merchant_markdown
from roco_push_console.config import ConfigStore, Settings
from roco_push_console.push import (
    DeliveryReport,
    NotificationMessage,
    ProviderConfig,
    PushResult,
    _WECOM_TOKEN_CACHE,
    send_delivery,
    send_provider,
)
from roco_push_console.rocom import process_merchant_data
from roco_push_console.scheduler import SchedulerService, next_run_after, parse_schedule_times
from roco_push_console.time_utils import get_round_info


class FakeResponse:
    def __init__(self, payload=None, status_code=200, text="OK"):
        self.payload = payload if payload is not None else {}
        self.status_code = status_code
        self.text = text
        self.reason = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = list(responses or [FakeResponse({"code": 0})])

    def _next(self):
        return self.responses.pop(0) if self.responses else FakeResponse({"code": 0})

    def post(self, url, data=None, json=None, headers=None, timeout=None, **kwargs):
        self.calls.append(
            {
                "method": "POST",
                "url": url,
                "data": data,
                "json": json,
                "headers": headers or {},
                "timeout": timeout,
                "kwargs": kwargs,
            }
        )
        return self._next()

    def get(self, url, params=None, timeout=None, **kwargs):
        self.calls.append(
            {
                "method": "GET",
                "url": url,
                "params": params,
                "timeout": timeout,
                "kwargs": kwargs,
            }
        )
        return self._next()


class CoreTests(unittest.TestCase):
    def make_settings(self, **overrides):
        values = {
            "rocom_api_key": "rocom-key",
            "game_api_url": "https://example.com/api",
            "notify_empty": False,
            "http_timeout": 30,
            "schedule_times": "08:01,12:01",
            "run_on_start": False,
            "delivery_mode": "all",
            "selected_provider": "serverchan-default",
            "failover_order": [],
            "providers": [
                ProviderConfig(
                    id="serverchan-default",
                    type="serverchan",
                    name="Server 酱",
                    enabled=True,
                    config={"sendkey": "send-key"},
                )
            ],
        }
        values.update(overrides)
        return Settings(**values)

    def test_round_info_before_open(self):
        now = datetime(2026, 4, 26, 7, 30, tzinfo=timezone(timedelta(hours=8)))
        self.assertEqual(get_round_info(now)["current"], "未开放")

    def test_process_merchant_data_filters_current_round(self):
        tz = timezone(timedelta(hours=8))
        now = datetime(2026, 4, 26, 9, 0, tzinfo=tz)
        active_start = int(datetime(2026, 4, 26, 8, 0, tzinfo=tz).timestamp() * 1000)
        active_end = int(datetime(2026, 4, 26, 12, 0, tzinfo=tz).timestamp() * 1000)
        expired_start = int(datetime(2026, 4, 26, 0, 0, tzinfo=tz).timestamp() * 1000)
        expired_end = int(datetime(2026, 4, 26, 4, 0, tzinfo=tz).timestamp() * 1000)
        data = {
            "merchantActivities": [
                {
                    "name": "远行商人",
                    "get_props": [
                        {"name": "当前商品", "start_time": active_start, "end_time": active_end},
                        {"name": "过期商品", "start_time": expired_start, "end_time": expired_end},
                    ],
                    "get_pets": [],
                }
            ]
        }

        processed = process_merchant_data(data, now=now)

        self.assertEqual(processed["product_count"], 1)
        self.assertEqual(processed["products"][0]["name"], "当前商品")

    def test_merchant_markdown_contains_products(self):
        processed = {
            "round_info": {"current": 1, "total": 4, "countdown": "3小时"},
            "products": [{"name": "咕噜球", "time_label": "08:00 - 12:00"}],
        }

        markdown = build_merchant_markdown(processed)

        self.assertIn("咕噜球", markdown)
        self.assertIn("当前轮次：1/4", markdown)

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

    def test_config_store_migrates_legacy_serverchan_sendkey(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text(
                '{"rocom_api_key":"rocom","serverchan_sendkey":"sct","schedule_times":"08:01"}',
                encoding="utf-8",
            )

            settings = ConfigStore(path).load()

            self.assertEqual(settings.rocom_api_key, "rocom")
            self.assertEqual(settings.providers[0].type, "serverchan")
            self.assertEqual(settings.providers[0].config["sendkey"], "sct")

    def test_config_store_preserves_nested_secret_when_blank_update(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ConfigStore(Path(temp_dir) / "config.json")
            original = Settings(
                rocom_api_key="rocom-key",
                game_api_url="https://example.com/api",
                notify_empty=False,
                http_timeout=30,
                schedule_times="08:01,12:01",
                run_on_start=False,
                delivery_mode="all",
                selected_provider="serverchan-default",
                failover_order=[],
                providers=[
                    ProviderConfig(
                        id="serverchan-default",
                        type="serverchan",
                        name="Server 酱",
                        enabled=True,
                        config={"sendkey": "send-key"},
                    )
                ],
            )
            store.save(original)

            updated = store.update(
                {
                    "rocom_api_key": "",
                    "notify_empty": True,
                    "providers": [
                        {
                            "id": "serverchan-default",
                            "type": "serverchan",
                            "name": "Server 酱",
                            "enabled": True,
                            "config": {"sendkey": ""},
                        }
                    ],
                }
            )

            self.assertEqual(updated.rocom_api_key, "rocom-key")
            self.assertEqual(updated.providers[0].config["sendkey"], "send-key")
            self.assertTrue(updated.notify_empty)

    def test_config_store_backs_up_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text("{broken-json", encoding="utf-8")
            store = ConfigStore(path)

            settings = store.load()

            self.assertEqual(settings.schedule_times, "08:05,12:05,16:05,20:05")
            self.assertIsNotNone(store.load_issue_dict())
            issue = store.load_issue_dict() or {}
            self.assertIn("配置读取失败", issue["message"])
            self.assertTrue(issue["backup_path"])
            self.assertTrue(Path(issue["backup_path"]).exists())
            self.assertFalse(path.exists())

    def test_launcher_normalizes_headless_modes(self):
        from roco_push_console.launcher import normalize_app_mode

        self.assertEqual(normalize_app_mode(""), "auto")
        self.assertEqual(normalize_app_mode("auto"), "auto")
        self.assertEqual(normalize_app_mode("console"), "web")
        self.assertEqual(normalize_app_mode("headless"), "scheduler")
        self.assertEqual(normalize_app_mode("managed"), "scheduler")
        self.assertEqual(normalize_app_mode("cron"), "scheduler")
        self.assertEqual(normalize_app_mode("once"), "once")

    def test_launcher_auto_mode_dispatches_scheduler_when_keys_are_configured(self):
        from roco_push_console import launcher

        env = {
            "ROCOM_API_KEY": "rocom-key",
            "SERVERCHAN_SENDKEY": "send-key",
            "CONFIG_PATH": str(Path(tempfile.gettempdir()) / "missing-roco-config.json"),
        }
        with patch.dict("os.environ", env, clear=True), patch.object(
            launcher.scheduler,
            "cli",
            side_effect=SystemExit(7),
        ) as scheduler_cli, patch.object(launcher.web, "cli") as web_cli:
            with self.assertRaises(SystemExit) as caught:
                launcher.main()

        self.assertEqual(caught.exception.code, 7)
        scheduler_cli.assert_called_once_with()
        web_cli.assert_not_called()

    def test_launcher_auto_mode_keeps_web_when_required_keys_are_missing(self):
        from roco_push_console import launcher

        with patch.dict("os.environ", {}, clear=True), patch.object(
            launcher.web,
            "cli",
            side_effect=SystemExit(8),
        ) as web_cli, patch.object(launcher.scheduler, "cli") as scheduler_cli:
            with self.assertRaises(SystemExit) as caught:
                launcher.main()

        self.assertEqual(caught.exception.code, 8)
        web_cli.assert_called_once_with()
        scheduler_cli.assert_not_called()

    def test_launcher_dispatches_scheduler_mode(self):
        from roco_push_console import launcher

        with patch.dict("os.environ", {"APP_MODE": "scheduler"}), patch.object(
            launcher.scheduler,
            "cli",
            side_effect=SystemExit(7),
        ) as scheduler_cli:
            with self.assertRaises(SystemExit) as caught:
                launcher.main()

        self.assertEqual(caught.exception.code, 7)
        scheduler_cli.assert_called_once_with()

    def test_healthcheck_skips_socket_for_scheduler_mode(self):
        from roco_push_console import healthcheck

        with patch.dict("os.environ", {"APP_MODE": "scheduler"}), patch(
            "socket.create_connection"
        ) as create_connection:
            self.assertEqual(healthcheck.main(), 0)

        create_connection.assert_not_called()

    def test_healthcheck_skips_socket_when_auto_mode_resolves_to_scheduler(self):
        from roco_push_console import healthcheck

        env = {
            "ROCOM_API_KEY": "rocom-key",
            "SERVERCHAN_SENDKEY": "send-key",
            "CONFIG_PATH": str(Path(tempfile.gettempdir()) / "missing-roco-config.json"),
        }
        with patch.dict("os.environ", env, clear=True), patch("socket.create_connection") as create_connection:
            self.assertEqual(healthcheck.main(), 0)

        create_connection.assert_not_called()

    def test_settings_from_env_builds_headless_provider(self):
        with patch.dict(
            "os.environ",
            {
                "ROCOM_API_KEY": "rocom-key",
                "PUSHPLUS_TOKEN": "push-token",
                "PUSHPLUS_TOPIC": "team",
            },
            clear=True,
        ):
            settings = Settings.from_env()

        self.assertEqual(settings.rocom_api_key, "rocom-key")
        self.assertEqual(settings.selected_provider, "pushplus-env")
        self.assertEqual(settings.failover_order, ["pushplus-env"])
        self.assertEqual(settings.providers[0].type, "pushplus")
        self.assertEqual(settings.providers[0].config["token"], "push-token")
        self.assertEqual(settings.providers[0].config["topic"], "team")

    def test_settings_from_env_uses_defaults_when_optional_envs_are_blank(self):
        with patch.dict(
            "os.environ",
            {
                "ROCOM_API_KEY": "rocom-key",
                "SERVERCHAN_SENDKEY": "send-key",
                "ROCOM_API_URL": "",
                "SCHEDULE_TIMES": "",
            },
            clear=True,
        ):
            settings = Settings.from_env()

        self.assertEqual(
            settings.game_api_url,
            "https://wegame.shallow.ink/api/v1/games/rocom/merchant/info?refresh=true",
        )
        self.assertEqual(settings.schedule_times, "08:05,12:05,16:05,20:05")

    def test_settings_from_env_applies_provider_defaults(self):
        with patch.dict(
            "os.environ",
            {"ROCOM_API_KEY": "rocom-key", "BARK_DEVICE_KEY": "device-key"},
            clear=True,
        ):
            settings = Settings.from_env()

        self.assertEqual(settings.providers[0].type, "bark")
        self.assertEqual(settings.providers[0].config["server_url"], "https://api.day.app")
        self.assertEqual(settings.providers[0].config["group"], "洛克王国")

    def test_settings_from_env_ignores_incomplete_headless_provider(self):
        with patch.dict(
            "os.environ",
            {"ROCOM_API_KEY": "rocom-key", "DINGTALK_SECRET": "signing-secret"},
            clear=True,
        ):
            settings = Settings.from_env()

        self.assertEqual(settings.providers, [])

    def test_public_config_masks_provider_secrets(self):
        settings = Settings(
            rocom_api_key="rocom-key",
            game_api_url="https://example.com/api",
            notify_empty=False,
            http_timeout=30,
            schedule_times="08:01",
            run_on_start=False,
            delivery_mode="all",
            selected_provider="",
            failover_order=[],
            providers=[
                ProviderConfig(
                    id="p1",
                    type="pushplus",
                    name="PushPlus",
                    enabled=True,
                    config={"token": "secret-token", "topic": "team"},
                )
            ],
        )

        public = settings.public_dict()

        self.assertEqual(public["rocom_api_key"], "")
        self.assertEqual(public["providers"][0]["config"]["token"], "")
        self.assertTrue(public["providers"][0]["config"]["has_token"])
        self.assertEqual(public["providers"][0]["config"]["topic"], "team")

    def test_serverchan_provider_posts_expected_payload(self):
        provider = ProviderConfig("p1", "serverchan", "Server 酱", True, {"sendkey": "SCT123"})
        message = NotificationMessage("标题", "摘要", "正文")
        session = FakeSession([FakeResponse({"code": 0})])

        result = send_provider(provider, message, session=session, timeout=7)

        self.assertTrue(result.success)
        self.assertEqual(session.calls[0]["url"], "https://sctapi.ftqq.com/SCT123.send")
        self.assertEqual(session.calls[0]["data"], {"title": "标题", "desp": "正文"})
        self.assertEqual(session.calls[0]["timeout"], 7)

    def test_serverchan_success_message_redacts_readkey(self):
        provider = ProviderConfig("p1", "serverchan", "Server 酱", True, {"sendkey": "SCT123"})
        message = NotificationMessage("标题", "摘要", "正文")
        session = FakeSession(
            [
                FakeResponse(
                    {
                        "code": 0,
                        "message": "",
                        "data": {
                            "pushid": "34197705",
                            "readkey": "SCTE0rv9wOx1IkO",
                            "error": "SUCCESS",
                        },
                    }
                )
            ]
        )

        result = send_provider(provider, message, session=session)

        self.assertTrue(result.success)
        self.assertIn("[已脱敏]", result.message)
        self.assertNotIn("SCTE0rv9wOx1IkO", result.message)

    def test_settings_failover_order_follows_enabled_provider_order(self):
        settings = Settings.from_mapping(
            {
                "delivery_mode": "failover",
                "failover_order": ["old-b", "old-a"],
                "providers": [
                    {
                        "id": "new-a",
                        "type": "serverchan",
                        "name": "A",
                        "enabled": True,
                        "config": {"sendkey": "a"},
                    },
                    {
                        "id": "disabled",
                        "type": "serverchan",
                        "name": "Disabled",
                        "enabled": False,
                        "config": {"sendkey": "disabled"},
                    },
                    {
                        "id": "new-b",
                        "type": "serverchan",
                        "name": "B",
                        "enabled": True,
                        "config": {"sendkey": "b"},
                    },
                ],
            }
        )

        self.assertEqual(settings.failover_order, ["new-a", "new-b"])

    def test_settings_selected_provider_falls_back_to_first_enabled_provider(self):
        settings = Settings.from_mapping(
            {
                "delivery_mode": "single",
                "selected_provider": "deleted-provider",
                "providers": [
                    {
                        "id": "disabled",
                        "type": "serverchan",
                        "name": "Disabled",
                        "enabled": False,
                        "config": {"sendkey": "disabled"},
                    },
                    {
                        "id": "first-enabled",
                        "type": "serverchan",
                        "name": "First",
                        "enabled": True,
                        "config": {"sendkey": "first"},
                    },
                ],
            }
        )

        self.assertEqual(settings.selected_provider, "first-enabled")

    def test_push_error_message_redacts_provider_secrets(self):
        class BrokenSession:
            def post(self, url, **kwargs):
                raise RuntimeError(f"failed POST {url}?access_token=LIVE_TOKEN&token=abc")

        provider = ProviderConfig("p1", "serverchan", "Server 酱", True, {"sendkey": "SCT_SECRET"})

        result = send_provider(
            provider,
            NotificationMessage("标题", "摘要", "正文"),
            session=BrokenSession(),
        )

        self.assertFalse(result.success)
        self.assertIn("[已脱敏]", result.message)
        self.assertNotIn("SCT_SECRET", result.message)
        self.assertNotIn("LIVE_TOKEN", result.message)
        self.assertNotIn("token=abc", result.message)

    def test_http_error_message_redacts_provider_secrets(self):
        provider = ProviderConfig(
            "p1",
            "gotify",
            "Gotify",
            True,
            {"base_url": "https://gotify.example", "app_token": "APP_TOKEN"},
        )
        session = FakeSession([FakeResponse({}, status_code=500, text="bad token=abc APP_TOKEN")])

        result = send_provider(provider, NotificationMessage("标题", "摘要", "正文"), session=session)

        self.assertFalse(result.success)
        self.assertNotIn("APP_TOKEN", result.message)
        self.assertNotIn("token=abc", result.message)

    def test_run_once_clears_stale_delivery_report_when_empty_is_skipped(self):
        app_module.LAST_DELIVERY_REPORT = DeliveryReport(
            True,
            "all",
            [PushResult("old", "旧通道", "serverchan", True, "old")],
        )
        settings = self.make_settings(notify_empty=False)

        with patch.object(app_module, "fetch_merchant_data", return_value={"merchantActivities": []}):
            exit_code = app_module.run_once(settings)

        self.assertEqual(exit_code, 0)
        self.assertIsNone(app_module.get_last_delivery_report())

    def test_run_once_returns_delivery_report(self):
        settings = self.make_settings(notify_empty=True)
        report = DeliveryReport(True, "all", [PushResult("p1", "通道", "serverchan", True, "ok")])
        raw_data = {
            "merchantActivities": [
                {
                    "name": "远行商人",
                    "get_props": [{"name": "咕噜球"}],
                    "get_pets": [],
                }
            ]
        }

        with patch.object(app_module, "fetch_merchant_data", return_value=raw_data), patch.object(
            app_module,
            "send_delivery",
            return_value=report,
        ):
            result = app_module.run_once(settings)

        self.assertEqual(result.exit_code, 0)
        self.assertIs(result.report, report)

    def test_scheduler_clears_stale_push_results_when_no_report(self):
        async def exercise():
            with tempfile.TemporaryDirectory() as temp_dir:
                store = ConfigStore(Path(temp_dir) / "config.json")
                store.save(self.make_settings())
                scheduler = SchedulerService(store)
                scheduler.state.last_push_results = [{"provider_name": "旧结果"}]
                with patch(
                    "roco_push_console.scheduler.run",
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
                with patch("roco_push_console.scheduler.run", new=AsyncMock(return_value=run_result)):
                    await scheduler._run_once("测试执行")
                return scheduler.state.last_push_results

        self.assertEqual(asyncio.run(exercise())[0]["provider_id"], "p1")

    def test_rendered_pages_reference_static_assets(self):
        login_html = web_module.render_login_html()
        index_html = web_module.render_index_html()

        self.assertIn("/static/login.css", login_html)
        self.assertIn("/static/login.js", login_html)
        self.assertIn("/static/console.css", index_html)
        self.assertIn("/static/console.js", index_html)

    def test_static_asset_route_serves_static_files(self):
        request = SimpleNamespace(scope={"method": "GET", "headers": []})

        response = asyncio.run(web_module.static_asset("login.css", request))

        self.assertEqual(response.status_code, 200)

    def test_push_uses_configured_timeout(self):
        settings = self.make_settings(http_timeout=42, notify_empty=True)
        raw_data = {
            "merchantActivities": [
                {
                    "name": "远行商人",
                    "get_props": [{"name": "咕噜球"}],
                    "get_pets": [],
                }
            ]
        }

        with patch.object(app_module, "fetch_merchant_data", return_value=raw_data), patch.object(
            app_module,
            "send_delivery",
            return_value=DeliveryReport(True, "all", []),
        ) as send_mock:
            exit_code = app_module.run_once(settings)

        self.assertEqual(exit_code, 0)
        self.assertEqual(send_mock.call_args.kwargs["options"].timeout, 42)

    def test_test_push_payload_uses_draft_config_without_saving(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            original_store = web_module.store
            try:
                store = ConfigStore(path)
                store.save(
                    self.make_settings(
                        providers=[
                            ProviderConfig(
                                "saved",
                                "serverchan",
                                "已保存",
                                True,
                                {"sendkey": "saved-key"},
                            )
                        ]
                    )
                )
                web_module.store = store

                settings = web_module._settings_from_test_payload(
                    {
                        "config": {
                            "providers": [
                                {
                                    "id": "draft",
                                    "type": "serverchan",
                                    "name": "草稿",
                                    "enabled": True,
                                    "config": {"sendkey": "draft-key"},
                                }
                            ],
                        }
                    }
                )

                self.assertEqual(settings.providers[0].id, "draft")
                self.assertEqual(settings.providers[0].config["sendkey"], "draft-key")
                saved = store.load()
                self.assertEqual(saved.providers[0].id, "saved")
            finally:
                web_module.store = original_store

    def test_pushplus_provider_posts_expected_payload(self):
        provider = ProviderConfig("p1", "pushplus", "PushPlus", True, {"token": "tok", "topic": "ops"})
        message = NotificationMessage("标题", "摘要", "正文")
        session = FakeSession([FakeResponse({"code": 200})])

        result = send_provider(provider, message, session=session)

        self.assertTrue(result.success)
        self.assertEqual(session.calls[0]["url"], "https://www.pushplus.plus/send")
        self.assertEqual(session.calls[0]["json"]["token"], "tok")
        self.assertEqual(session.calls[0]["json"]["template"], "markdown")
        self.assertEqual(session.calls[0]["json"]["topic"], "ops")

    def test_wecomchan_token_is_cached(self):
        _WECOM_TOKEN_CACHE.clear()
        provider = ProviderConfig(
            "p1",
            "wecomchan",
            "企微应用",
            True,
            {"corpid": "corp", "secret": "sec", "agentid": "1001", "touser": "@all"},
        )
        message = NotificationMessage("标题", "摘要", "正文")
        session = FakeSession(
            [
                FakeResponse({"errcode": 0, "access_token": "token", "expires_in": 7200}),
                FakeResponse({"errcode": 0}),
                FakeResponse({"errcode": 0}),
            ]
        )

        first = send_provider(provider, message, session=session)
        second = send_provider(provider, message, session=session)

        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(sum(1 for call in session.calls if call["method"] == "GET"), 1)
        self.assertEqual(sum(1 for call in session.calls if call["method"] == "POST"), 2)

    def test_delivery_all_succeeds_when_at_least_one_provider_succeeds(self):
        providers = [
            ProviderConfig("bad", "serverchan", "Bad", True, {"sendkey": "bad"}),
            ProviderConfig("ok", "serverchan", "Ok", True, {"sendkey": "ok"}),
        ]
        message = NotificationMessage("标题", "摘要", "正文")
        session = FakeSession([FakeResponse({"code": 1, "message": "bad"}), FakeResponse({"code": 0})])

        report = send_delivery(providers, message, mode="all", session=session)

        self.assertTrue(report.success)
        self.assertEqual(len(report.results), 2)

    def test_delivery_single_uses_selected_provider_only(self):
        providers = [
            ProviderConfig("a", "serverchan", "A", True, {"sendkey": "a"}),
            ProviderConfig("b", "serverchan", "B", True, {"sendkey": "b"}),
        ]
        session = FakeSession([FakeResponse({"code": 0})])

        report = send_delivery(
            providers,
            NotificationMessage("标题", "摘要", "正文"),
            mode="single",
            selected_provider="b",
            session=session,
        )

        self.assertTrue(report.success)
        self.assertEqual(len(report.results), 1)
        self.assertIn("/b.send", session.calls[0]["url"])

    def test_delivery_failover_stops_after_first_success(self):
        providers = [
            ProviderConfig("a", "serverchan", "A", True, {"sendkey": "a"}),
            ProviderConfig("b", "serverchan", "B", True, {"sendkey": "b"}),
            ProviderConfig("c", "serverchan", "C", True, {"sendkey": "c"}),
        ]
        session = FakeSession([FakeResponse({"code": 1}), FakeResponse({"code": 0}), FakeResponse({"code": 0})])

        report = send_delivery(
            providers,
            NotificationMessage("标题", "摘要", "正文"),
            mode="failover",
            failover_order=["a", "b", "c"],
            session=session,
        )

        self.assertTrue(report.success)
        self.assertEqual(len(report.results), 2)
        self.assertEqual(len(session.calls), 2)

    def test_delivery_failover_defaults_to_enabled_provider_order(self):
        providers = [
            ProviderConfig("a", "serverchan", "A", True, {"sendkey": "a"}),
            ProviderConfig("off", "serverchan", "Off", False, {"sendkey": "off"}),
            ProviderConfig("b", "serverchan", "B", True, {"sendkey": "b"}),
        ]
        session = FakeSession([FakeResponse({"code": 1}), FakeResponse({"code": 0})])

        report = send_delivery(
            providers,
            NotificationMessage("标题", "摘要", "正文"),
            mode="failover",
            session=session,
        )

        self.assertTrue(report.success)
        self.assertEqual([result.provider_id for result in report.results], ["a", "b"])
        self.assertEqual(len(session.calls), 2)


if __name__ == "__main__":
    unittest.main()
