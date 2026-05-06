from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from roco_serverchan_notifier.config_store import ConfigStore


class ConfigStoreModuleTests(unittest.TestCase):
    def test_config_store_module_exposes_console_auth_reader(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text('{"console_auth":{"password_hash":"hash"}}', encoding="utf-8")

            store = ConfigStore(path)

            self.assertEqual(store.console_auth()["password_hash"], "hash")


if __name__ == "__main__":
    unittest.main()
