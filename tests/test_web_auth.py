from __future__ import annotations

import asyncio
import importlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    from .helpers import JsonRequest, RocoTestCase
except ImportError:
    from helpers import JsonRequest, RocoTestCase

from roco_serverchan_notifier import web as web_module
from roco_serverchan_notifier import web_auth, web_services
from roco_serverchan_notifier.config import ConfigStore
from roco_serverchan_notifier.push import ProviderConfig



class WebAuthTests(RocoTestCase):
    def test_web_auth_delegates_to_password_and_session_modules(self):
        password_module = importlib.import_module("roco_serverchan_notifier.console_password")
        session_module = importlib.import_module("roco_serverchan_notifier.console_session")

        self.assertIs(web_auth.auth_password, password_module.auth_password)
        self.assertIs(web_auth.check_auth_password, password_module.check_auth_password)
        self.assertIs(web_auth.make_session_cookie, session_module.make_session_cookie)
        self.assertIs(web_auth.valid_session_cookie, session_module.valid_session_cookie)
        self.assertEqual(web_auth.SESSION_COOKIE_NAME, session_module.SESSION_COOKIE_NAME)

    def test_rendered_pages_reference_static_assets(self):
        login_html = web_module.render_login_html()
        index_html = web_module.render_index_html()

        self.assertIn("/static/login.css", login_html)
        self.assertIn("/static/login.js", login_html)
        self.assertIn("/static/console.css", index_html)
        self.assertIn('type="module"', index_html)
        self.assertIn("/static/console.js", index_html)

    def test_static_asset_route_serves_static_files(self):
        request = SimpleNamespace(scope={"method": "GET", "headers": []})

        response = asyncio.run(web_module.static_asset("login.css", request))

        self.assertEqual(response.status_code, 200)

    def test_static_asset_route_serves_console_modules(self):
        request = SimpleNamespace(scope={"method": "GET", "headers": []})

        for path in ("console-api.js", "console-format.js", "console-providers.js"):
            response = asyncio.run(web_module.static_asset(path, request))
            self.assertEqual(response.status_code, 200, path)

    def test_console_generates_default_password_when_env_password_is_empty(self):
        request = SimpleNamespace(cookies={})

        with tempfile.TemporaryDirectory() as temp_dir:
            original_store = web_module.store
            try:
                web_module.store = ConfigStore(Path(temp_dir) / "config.json")
                with patch.dict("os.environ", {}, clear=True):
                    web_auth.reset_generated_password_for_tests()
                    password = web_auth.auth_password(web_module.store)

                self.assertGreaterEqual(len(password), 32)
                self.assertFalse(web_auth.is_authenticated(web_module.store, request))
            finally:
                web_module.store = original_store
                web_auth.reset_generated_password_for_tests()

    def test_console_generates_default_password_hash_and_logs_plaintext_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            original_store = web_module.store
            try:
                web_module.store = ConfigStore(path)
                with patch.dict("os.environ", {}, clear=True), patch("builtins.print") as print_mock:
                    web_auth.reset_generated_password_for_tests()
                    web_auth.log_console_password_once(web_module.store)
                    web_auth.log_console_password_once(web_module.store)

                saved_text = path.read_text(encoding="utf-8")
                saved = json.loads(saved_text)
                auth = saved["console_auth"]
                self.assertRegex(auth["password_hash"], r"^pbkdf2_sha256\$\d+\$")

                output = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)
                password_line = next(
                    line for line in output.splitlines() if line.startswith("控制台默认密码: ")
                )
                password = password_line.removeprefix("控制台默认密码: ")
                self.assertGreaterEqual(len(password), 32)
                self.assertNotIn(password, saved_text)
                self.assertEqual(output.count("控制台默认密码:"), 1)
            finally:
                web_module.store = original_store
                web_auth.reset_generated_password_for_tests()

    def test_console_password_generation_falls_back_when_hash_cannot_be_saved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_store = web_module.store
            try:
                web_module.store = ConfigStore(Path(temp_dir) / "config.json")
                with patch.dict("os.environ", {}, clear=True), patch(
                    "builtins.print"
                ) as print_mock, patch.object(
                    web_module.store,
                    "save_console_auth",
                    side_effect=OSError("read-only"),
                ):
                    web_auth.reset_generated_password_for_tests()
                    web_auth.log_console_password_once(web_module.store)

                output = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)
                self.assertIn("控制台默认密码", output)
                self.assertIn("未能保存", output)
            finally:
                web_module.store = original_store
                web_auth.reset_generated_password_for_tests()

    def test_stored_console_password_hash_is_cached_until_reset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            auth = {"password_hash": "pbkdf2_sha256$1$salt$digest"}
            payload = self.make_settings().to_dict()
            payload["console_auth"] = auth
            path.write_text(json.dumps(payload), encoding="utf-8")
            original_store = web_module.store
            try:
                web_module.store = ConfigStore(path)
                web_auth.reset_generated_password_for_tests()
                with patch.object(web_module.store, "console_auth", wraps=web_module.store.console_auth) as auth_mock:
                    self.assertEqual(web_auth.stored_console_password_hash(web_module.store), auth["password_hash"])
                    self.assertEqual(web_auth.stored_console_password_hash(web_module.store), auth["password_hash"])
                    self.assertEqual(auth_mock.call_count, 1)

                    web_auth.reset_console_auth_cache()
                    self.assertEqual(web_auth.stored_console_password_hash(web_module.store), auth["password_hash"])
                    self.assertEqual(auth_mock.call_count, 2)
            finally:
                web_module.store = original_store
                web_auth.reset_generated_password_for_tests()

    def test_persisted_console_password_survives_restart_without_relogging(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            original_store = web_module.store
            try:
                web_module.store = ConfigStore(path)
                with patch.dict("os.environ", {}, clear=True), patch("builtins.print") as print_mock:
                    web_auth.reset_generated_password_for_tests()
                    web_auth.log_console_password_once(web_module.store)
                output = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)
                password_line = next(
                    line for line in output.splitlines() if line.startswith("控制台默认密码: ")
                )
                password = password_line.removeprefix("控制台默认密码: ")

                web_auth.reset_generated_password_for_tests()
                with patch.dict("os.environ", {}, clear=True), patch("builtins.print") as relog_mock:
                    web_auth.log_console_password_once(web_module.store)
                    response = asyncio.run(
                        web_module.api_login(JsonRequest({"username": "admin", "password": password}))
                    )

                self.assertEqual(relog_mock.call_count, 0)
                self.assertEqual(response.status_code, 200)
                self.assertIn(web_module.SESSION_COOKIE_NAME, response.headers.get("set-cookie", ""))
            finally:
                web_module.store = original_store
                web_auth.reset_generated_password_for_tests()

    def test_generated_console_session_cookie_survives_restart(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            original_store = web_module.store
            try:
                web_module.store = ConfigStore(path)
                with patch.dict("os.environ", {}, clear=True), patch("builtins.print"):
                    web_auth.reset_generated_password_for_tests()
                    web_auth.log_console_password_once(web_module.store)
                    cookie = web_auth.make_session_cookie(web_module.store, "admin")

                    request = SimpleNamespace(cookies={web_module.SESSION_COOKIE_NAME: cookie})
                    self.assertTrue(web_auth.is_authenticated(web_module.store, request))

                    web_auth.reset_generated_password_for_tests()
                    self.assertTrue(web_auth.is_authenticated(web_module.store, request))
            finally:
                web_module.store = original_store
                web_auth.reset_generated_password_for_tests()

    def test_console_password_env_takes_precedence_without_writing_console_auth(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            original_store = web_module.store
            try:
                web_module.store = ConfigStore(path)
                with patch.dict("os.environ", {"CONSOLE_PASSWORD": "fixed-secret"}, clear=True):
                    web_auth.reset_generated_password_for_tests()
                    self.assertEqual(web_auth.auth_password(web_module.store), "fixed-secret")
                    web_auth.log_console_password_once(web_module.store)

                self.assertFalse(path.exists())
            finally:
                web_module.store = original_store
                web_auth.reset_generated_password_for_tests()

    def test_console_can_explicitly_allow_empty_password(self):
        request = SimpleNamespace(cookies={})

        with patch.dict("os.environ", {"CONSOLE_ALLOW_EMPTY_PASSWORD": "true"}, clear=True):
            web_auth.reset_generated_password_for_tests()
            self.assertTrue(web_auth.is_authenticated(web_module.store, request))

    def test_login_page_shows_form_when_using_generated_password(self):
        request = SimpleNamespace(cookies={})

        with tempfile.TemporaryDirectory() as temp_dir:
            original_store = web_module.store
            try:
                web_module.store = ConfigStore(Path(temp_dir) / "config.json")
                with patch.dict("os.environ", {}, clear=True):
                    web_auth.reset_generated_password_for_tests()
                    response = asyncio.run(web_module.login_page(request))
            finally:
                web_module.store = original_store
                web_auth.reset_generated_password_for_tests()

        self.assertEqual(response.status_code, 200)
        self.assertIn("/static/login.js", response.body.decode("utf-8"))

    def test_generated_console_password_is_logged_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_store = web_module.store
            try:
                web_module.store = ConfigStore(Path(temp_dir) / "config.json")
                with patch.dict("os.environ", {}, clear=True), patch("builtins.print") as print_mock:
                    web_auth.reset_generated_password_for_tests()
                    password = web_auth.auth_password(web_module.store)

                    web_auth.log_console_password_once(web_module.store)
                    web_auth.log_console_password_once(web_module.store)
            finally:
                web_module.store = original_store
                web_auth.reset_generated_password_for_tests()

        output = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)
        self.assertIn("控制台默认密码", output)
        self.assertIn(password, output)
        self.assertEqual(output.count(password), 1)

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

                settings = web_services.settings_from_test_payload(
                    web_module.store,
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


    def test_generated_password_authenticates_through_extracted_module(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            auth_store = ConfigStore(Path(temp_dir) / "config.json")
            request = SimpleNamespace(cookies={})

            with patch.dict("os.environ", {}, clear=True), patch("builtins.print"):
                web_auth.reset_generated_password_for_tests()
                password = web_auth.auth_password(auth_store)

            self.assertGreaterEqual(len(password), 32)
            self.assertTrue(web_auth.check_auth_password(auth_store, password))
            self.assertFalse(web_auth.is_authenticated(auth_store, request))


if __name__ == "__main__":
    unittest.main()
