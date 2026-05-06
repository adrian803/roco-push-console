from __future__ import annotations

import unittest
from unittest.mock import patch

from roco_serverchan_notifier.settings import DEFAULT_GAME_API_URL, DEFAULT_SCHEDULE_TIMES, Settings


class SettingsModuleTests(unittest.TestCase):
    def test_settings_module_reads_defaults_from_env(self):
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

        self.assertEqual(settings.game_api_url, DEFAULT_GAME_API_URL)
        self.assertEqual(settings.schedule_times, DEFAULT_SCHEDULE_TIMES)


if __name__ == "__main__":
    unittest.main()
