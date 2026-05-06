from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from roco_serverchan_notifier.config import ConfigStore
from roco_serverchan_notifier.push import DeliveryReport, PushResult
from roco_serverchan_notifier.web_services import (
    build_state_payload,
    save_config_payload,
    send_test_push,
    settings_from_test_payload,
)

try:
    from .helpers import FakeSession, RocoTestCase
except ImportError:
    from helpers import FakeSession, RocoTestCase


class WebServicesTests(RocoTestCase):
    def test_build_state_payload_keeps_existing_api_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ConfigStore(Path(temp_dir) / "config.json")
            store.save(self.make_settings())
            scheduler = SimpleNamespace(state=SimpleNamespace(to_dict=lambda: {"running": True}))

            payload = build_state_payload(store, scheduler)

        self.assertIn("config", payload)
        self.assertIn("config_issue", payload)
        self.assertIn("provider_types", payload)
        self.assertEqual(payload["scheduler"], {"running": True})
        self.assertIn("auth_enabled", payload)
        self.assertIn("now", payload)

    def test_build_state_payload_hides_provider_env_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ConfigStore(Path(temp_dir) / "config.json")
            store.save(self.make_settings())
            scheduler = SimpleNamespace(state=SimpleNamespace(to_dict=lambda: {"running": True}))

            payload = build_state_payload(store, scheduler)

        spec = payload["provider_types"]["serverchan"]
        self.assertIn("fields", spec)
        self.assertEqual(set(spec), {"label", "description", "fields"})


    def test_save_config_payload_validates_schedule_and_provider_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ConfigStore(Path(temp_dir) / "config.json")
            store.save(self.make_settings())
            scheduler = SimpleNamespace(wake=lambda: None)

            with self.assertRaisesRegex(ValueError, "未知通道类型"):
                save_config_payload(store, scheduler, {"schedule_times": "08:01", "providers": [{"type": "unknown"}]})

            with self.assertRaisesRegex(ValueError, "定时格式"):
                save_config_payload(store, scheduler, {"schedule_times": "bad", "providers": []})

    def test_settings_from_test_payload_rejects_unknown_provider_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ConfigStore(Path(temp_dir) / "config.json")
            store.save(self.make_settings())

            with self.assertRaisesRegex(ValueError, "未知通道类型"):
                settings_from_test_payload(store, {"config": {"providers": [{"type": "unknown"}]}})

    def test_send_test_push_single_provider_uses_draft_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ConfigStore(Path(temp_dir) / "config.json")
            store.save(self.make_settings())
            session = FakeSession()
            result = PushResult("serverchan-default", "Server 酱", "serverchan", True, "ok")

            with patch("roco_serverchan_notifier.web_services.send_provider", return_value=result) as send_mock:
                payload = asyncio.run(
                    send_test_push(
                        store,
                        {"provider_id": "serverchan-default", "config": self.make_settings().to_dict()},
                        session=session,
                    )
                )

        self.assertEqual(payload["message"], "Server 酱 测试推送已发送")
        self.assertEqual(payload["results"], [result.to_dict()])
        self.assertIs(send_mock.call_args.kwargs["session"], session)

    def test_send_test_push_strategy_returns_delivery_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ConfigStore(Path(temp_dir) / "config.json")
            store.save(self.make_settings())
            result = PushResult("p1", "通道", "serverchan", True, "ok")
            report = DeliveryReport(True, "all", [result])

            with patch("roco_serverchan_notifier.web_services.send_delivery", return_value=report):
                payload = asyncio.run(send_test_push(store, {"config": self.make_settings().to_dict()}))

        self.assertEqual(payload["message"], "测试推送已发送")
        self.assertEqual(payload["results"], [result.to_dict()])


if __name__ == "__main__":
    unittest.main()
