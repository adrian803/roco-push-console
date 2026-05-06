from __future__ import annotations

import importlib
import threading
import unittest
from unittest.mock import patch

try:
    from .helpers import FakeResponse, FakeSession, RocoTestCase, SessionFactory, load_cross_runtime_fixture
except ImportError:
    from helpers import FakeResponse, FakeSession, RocoTestCase, SessionFactory, load_cross_runtime_fixture

from roco_serverchan_notifier import app as app_module
from roco_serverchan_notifier import push as push_module
from roco_serverchan_notifier.provider_specs import PROVIDER_TYPES
from roco_serverchan_notifier.push import (
    DeliveryReport,
    NotificationMessage,
    PROVIDER_SENDERS,
    ProviderConfig,
    PushResult,
    _WECOM_TOKEN_CACHE,
    send_delivery,
    send_provider,
)



class PushDeliveryTests(RocoTestCase):
    def test_push_provider_senders_are_grouped_by_family_modules(self):
        registry = importlib.import_module("roco_serverchan_notifier.push_provider_senders.registry")
        token = importlib.import_module("roco_serverchan_notifier.push_provider_senders.token")
        webhook = importlib.import_module("roco_serverchan_notifier.push_provider_senders.webhook")
        wecom = importlib.import_module("roco_serverchan_notifier.push_provider_senders.wecom")

        self.assertEqual(set(registry.PROVIDER_SENDERS), set(PROVIDER_SENDERS))
        self.assertEqual(set(registry.PROVIDER_SENDERS), set(PROVIDER_TYPES))
        self.assertIs(registry.PROVIDER_SENDERS["pushplus"], token.send_pushplus)
        self.assertIs(registry.PROVIDER_SENDERS["dingtalk_bot"], webhook.send_dingtalk_bot)
        self.assertIs(registry.PROVIDER_SENDERS["wecomchan"], wecom.send_wecomchan)

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

    def test_run_once_returns_no_report_when_empty_is_skipped(self):
        settings = self.make_settings(notify_empty=False)

        with patch.object(app_module, "fetch_merchant_data", return_value={"merchantActivities": []}):
            result = app_module.run_once(settings)

        self.assertEqual(result.exit_code, 0)
        self.assertIsNone(result.report)

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

    def test_sender_required_validation_accepts_manifest_defaults(self):
        provider = ProviderConfig("p1", "bark", "Bark", True, {"device_key": "device-key"})
        message = NotificationMessage("标题", "摘要", "正文")
        session = FakeSession([FakeResponse({"code": 0})])

        result = send_provider(provider, message, session=session)

        self.assertTrue(result.success)
        self.assertEqual(session.calls[0]["url"], "https://api.day.app/device-key")
        self.assertEqual(session.calls[0]["json"]["group"], "洛克王国")

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
        factory = SessionFactory(
            [[FakeResponse({"code": 1, "message": "bad"})], [FakeResponse({"code": 0})]]
        )

        with patch.object(push_module.requests, "Session", factory):
            report = send_delivery(providers, message, mode="all")

        self.assertTrue(report.success)
        self.assertEqual(len(report.results), 2)

    def test_delivery_all_does_not_share_passed_session_between_threads(self):
        providers = [
            ProviderConfig("a", "serverchan", "A", True, {"sendkey": "a"}),
            ProviderConfig("b", "serverchan", "B", True, {"sendkey": "b"}),
        ]
        shared_session = FakeSession([FakeResponse({"code": 0}), FakeResponse({"code": 0})])
        seen_sessions = []

        def fake_send_provider(provider, message, *, session=None, timeout=10):
            seen_sessions.append(session)
            return PushResult(provider.id, provider.name, provider.type, True, "ok")

        factory = SessionFactory()
        with patch.object(push_module.requests, "Session", factory), patch.object(
            push_module,
            "send_provider",
            side_effect=fake_send_provider,
        ):
            report = send_delivery(
                providers,
                NotificationMessage("标题", "摘要", "正文"),
                mode="all",
                session=shared_session,
            )

        self.assertTrue(report.success)
        self.assertEqual(len(seen_sessions), 2)
        self.assertNotIn(shared_session, seen_sessions)
        self.assertEqual(len({id(session) for session in seen_sessions}), 2)

    def test_delivery_all_sends_enabled_providers_concurrently(self):
        providers = [
            ProviderConfig("a", "serverchan", "A", True, {"sendkey": "a"}),
            ProviderConfig("b", "serverchan", "B", True, {"sendkey": "b"}),
        ]
        barrier = threading.Barrier(len(providers))

        def fake_send_provider(provider, message, *, session=None, timeout=10):
            try:
                barrier.wait(timeout=1)
            except threading.BrokenBarrierError as exc:
                raise AssertionError("all mode did not send providers concurrently") from exc
            return PushResult(provider.id, provider.name, provider.type, True, "ok")

        with patch.object(push_module, "send_provider", side_effect=fake_send_provider):
            report = send_delivery(providers, NotificationMessage("标题", "摘要", "正文"), mode="all")

        self.assertTrue(report.success)
        self.assertEqual([result.provider_id for result in report.results], ["a", "b"])

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


    def test_shared_delivery_summary_fixture_matches_python(self):
        fixture = load_cross_runtime_fixture()
        case = fixture["delivery_summary"]
        report_data = case["python_report"]
        results = [PushResult(**item) for item in report_data["results"]]
        report = DeliveryReport(report_data["success"], report_data["mode"], results)

        self.assertEqual(report.summary(), case["expected"])


if __name__ == "__main__":
    unittest.main()
