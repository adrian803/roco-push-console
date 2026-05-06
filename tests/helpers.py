from __future__ import annotations

import sys
import unittest
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from roco_serverchan_notifier.config import Settings
from roco_serverchan_notifier.push import ProviderConfig

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "cross_runtime_cases.json"


def load_cross_runtime_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class JsonRequest:
    def __init__(self, payload, scheme="http"):
        from types import SimpleNamespace

        self._payload = payload
        self.url = SimpleNamespace(scheme=scheme)

    async def json(self):
        return self._payload


class SessionFactory:
    def __init__(self, responses=None):
        self.sessions = []
        self.responses = list(responses or [])

    def __call__(self):
        responses = self.responses.pop(0) if self.responses else None
        session = FakeSession(responses)
        self.sessions.append(session)
        return session


class RocoTestCase(unittest.TestCase):
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
