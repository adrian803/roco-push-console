from __future__ import annotations

import unittest

try:
    from .helpers import FakeResponse, FakeSession
except ImportError:
    from helpers import FakeResponse, FakeSession

from roco_serverchan_notifier.push_http import JsonPostRequest, post_json
from roco_serverchan_notifier.push_models import ProviderConfig


class PushHttpTests(unittest.TestCase):
    def test_post_json_uses_success_codes_and_redacts_http_error_text(self):
        provider = ProviderConfig(
            id="p1",
            type="pushplus",
            name="PushPlus",
            enabled=True,
            config={"token": "secret-token"},
        )
        session = FakeSession([FakeResponse({}, status_code=500, text="bad token=abc secret-token")])

        result = post_json(
            JsonPostRequest(
                provider=provider,
                session=session,
                url="https://example.com/send",
                payload={"message": "hello"},
                timeout=30,
                success_codes={200, "200", 0, "0"},
            )
        )

        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 500)
        self.assertEqual(result.message, "bad token=[已脱敏] [已脱敏]")


if __name__ == "__main__":
    unittest.main()
