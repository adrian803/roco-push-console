from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from .helpers import RocoTestCase
except ImportError:
    from helpers import RocoTestCase

from roco_serverchan_notifier.config import ConfigStore, Settings
from roco_serverchan_notifier.push import ProviderConfig



class ConfigTests(RocoTestCase):
    def test_settings_reads_include_price_info_from_env(self):
        with patch.dict("os.environ", {"INCLUDE_PRICE_INFO": "true"}, clear=True):
            settings = Settings.from_env()

        self.assertTrue(settings.include_price_info)

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

    def test_config_store_preserves_console_auth_when_saving_business_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            auth = {
                "password_hash": "pbkdf2_sha256$1$salt$digest",
                "generated_at": "2026-05-02T00:00:00+08:00",
            }
            payload = self.make_settings().to_dict()
            payload["console_auth"] = auth
            path.write_text(json.dumps(payload), encoding="utf-8")
            store = ConfigStore(path)

            store.update({"notify_empty": True})

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["console_auth"], auth)

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
        from roco_serverchan_notifier.launcher import normalize_app_mode

        self.assertEqual(normalize_app_mode(""), "auto")
        self.assertEqual(normalize_app_mode("auto"), "auto")
        self.assertEqual(normalize_app_mode("console"), "web")
        self.assertEqual(normalize_app_mode("headless"), "scheduler")
        self.assertEqual(normalize_app_mode("managed"), "scheduler")
        self.assertEqual(normalize_app_mode("cron"), "scheduler")
        self.assertEqual(normalize_app_mode("once"), "once")

    def test_launcher_auto_mode_dispatches_scheduler_when_keys_are_configured(self):
        from roco_serverchan_notifier import launcher

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
        from roco_serverchan_notifier import launcher

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
        from roco_serverchan_notifier import launcher

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
        from roco_serverchan_notifier import healthcheck

        with patch.dict("os.environ", {"APP_MODE": "scheduler"}), patch(
            "socket.create_connection"
        ) as create_connection:
            self.assertEqual(healthcheck.main(), 0)

        create_connection.assert_not_called()

    def test_healthcheck_skips_socket_when_auto_mode_resolves_to_scheduler(self):
        from roco_serverchan_notifier import healthcheck

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
            "https://wegame.shallow.ink/api/v1/games/rocom/merchant/info",
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

    def test_settings_from_env_enables_wecom_bot_with_key_only(self):
        with patch.dict(
            "os.environ",
            {"ROCOM_API_KEY": "rocom-key", "WECOM_BOT_KEY": "bot-key"},
            clear=True,
        ):
            settings = Settings.from_env()

        self.assertEqual(settings.providers[0].type, "wecom_bot")
        self.assertEqual(settings.providers[0].config["key"], "bot-key")

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


if __name__ == "__main__":
    unittest.main()
