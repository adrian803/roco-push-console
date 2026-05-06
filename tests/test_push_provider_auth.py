from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    from .helpers import FakeResponse, FakeSession
except ImportError:
    from helpers import FakeResponse, FakeSession

from roco_serverchan_notifier.push_models import ProviderConfig
from roco_serverchan_notifier.push_provider_auth import (
    _WECOM_TOKEN_CACHE,
    append_dingtalk_sign,
    feishu_sign,
    get_wecom_token,
)


class PushProviderAuthTests(unittest.TestCase):
    def test_get_wecom_token_uses_cache(self):
        _WECOM_TOKEN_CACHE.clear()
        provider = ProviderConfig(
            id="p1",
            type="wecomchan",
            name="企微应用",
            enabled=True,
            config={"corpid": "corp", "secret": "sec"},
        )
        session = FakeSession(
            [
                FakeResponse({"errcode": 0, "access_token": "token", "expires_in": 7200}),
            ]
        )

        first = get_wecom_token(provider, session, 30)
        second = get_wecom_token(provider, session, 30)

        self.assertEqual(first, "token")
        self.assertEqual(second, "token")
        self.assertEqual(sum(1 for call in session.calls if call["method"] == "GET"), 1)

    def test_sign_helpers_return_expected_shapes(self):
        with patch("time.time", return_value=1700000000):
            webhook = append_dingtalk_sign("https://example.com/hook", "secret")

        self.assertIn("timestamp=", webhook)
        self.assertIn("sign=", webhook)
        self.assertTrue(feishu_sign("secret", "1700000000"))


if __name__ == "__main__":
    unittest.main()
