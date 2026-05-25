from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from telachat.client import ChatResult
from telachat.controller import TelachatController


class ControllerTests(unittest.TestCase):
    def test_theme_can_be_changed_through_controller(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                controller = TelachatController()
                try:
                    self.assertEqual(controller.theme().name, "system")
                    theme = controller.set_theme("dark")
                    self.assertEqual(theme.name, "dark")
                    self.assertEqual(controller.config.theme, "dark")
                    config_text = (Path(tmp) / "config" / "telachat" / "config.toml").read_text(
                        encoding="utf-8"
                    )
                    self.assertIn('theme = "dark"', config_text)
                finally:
                    controller.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_apply_prompt_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                config_dir = Path(tmp) / "config" / "telachat"
                config_dir.mkdir(parents=True)
                (config_dir / "config.toml").write_text(
                    """
                    default_profile = "test"

                    [profiles.test]
                    label = "Test"
                    base_url = "http://127.0.0.1:9/v1"
                    api_key = "test"
                    model = "demo"

                    [prompt_templates]
                    ticket = "Schreibe ein Ticket:\\n\\n{input}"
                    prefix = "Antworte knapp."
                    """,
                    encoding="utf-8",
                )
                controller = TelachatController()
                try:
                    self.assertEqual(
                        controller.apply_prompt_template("ticket", "Fehler beim Login"),
                        "Schreibe ein Ticket:\n\nFehler beim Login",
                    )
                    self.assertEqual(
                        controller.apply_prompt_template("prefix", "Fehler beim Login"),
                        "Antworte knapp.\n\nFehler beim Login",
                    )
                finally:
                    controller.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_regenerate_replaces_latest_assistant_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                config_dir = Path(tmp) / "config" / "telachat"
                config_dir.mkdir(parents=True)
                (config_dir / "config.toml").write_text(
                    """
                    default_profile = "test"
                    default_system_prompt = "System"
                    max_history_messages = 8

                    [profiles.test]
                    label = "Test"
                    base_url = "http://127.0.0.1:9/v1"
                    api_key = "test"
                    model = "demo"
                    models = ["demo", "demo-large"]
                    stream = false
                    """,
                    encoding="utf-8",
                )
                controller = TelachatController()
                try:
                    session, _messages = controller.new_session(
                        profile_name="test",
                        system_prompt="System",
                        title="Regenerate",
                    )
                    controller.store.add_message(session.id, "user", "Hallo")
                    controller.store.add_message(session.id, "assistant", "Alt")

                    with (
                        mock.patch("telachat.controller.OpenAICompatClient") as client_cls,
                        mock.patch("telachat.controller.time.perf_counter") as perf_counter,
                    ):
                        perf_counter.side_effect = [20.0, 20.75]
                        client_cls.return_value.chat.return_value = ChatResult(
                            content="Neu",
                            raw={},
                        )
                        payload = controller.regenerate(
                            session_id=session.id,
                            profile_name="test",
                            model="demo-large",
                            system_prompt="System",
                            temperature=0.25,
                            max_tokens=123,
                        )

                    selected_profile = client_cls.call_args.args[0]
                    self.assertEqual(selected_profile.temperature, 0.25)
                    self.assertEqual(selected_profile.max_tokens, 123)
                    self.assertEqual(payload.elapsed_seconds, 0.75)
                    self.assertEqual(payload.answer, "Neu")
                    self.assertEqual(payload.session.model, "demo-large")
                    self.assertEqual(
                        [(message.role, message.content) for message in payload.messages],
                        [("user", "Hallo"), ("assistant", "Neu")],
                    )
                    sent_messages = client_cls.return_value.chat.call_args.args[0]
                    self.assertEqual(
                        [item["role"] for item in sent_messages],
                        ["system", "user"],
                    )
                finally:
                    controller.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_edit_last_user_message_refreshes_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                controller = TelachatController()
                try:
                    session, _messages = controller.new_session(title="Edit")
                    controller.store.add_message(session.id, "user", "Alt")
                    controller.store.add_message(session.id, "assistant", "Antwort")

                    updated, messages = controller.edit_last_user_message(session.id, "Neu")

                    self.assertEqual(updated.id, session.id)
                    self.assertEqual(
                        [(message.role, message.content) for message in messages],
                        [("user", "Neu")],
                    )
                finally:
                    controller.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_fork_session_returns_new_history_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                controller = TelachatController()
                try:
                    session, _messages = controller.new_session(title="Original")
                    controller.store.add_message(session.id, "user", "Hallo")
                    controller.store.add_message(session.id, "assistant", "Hi")

                    fork, messages = controller.fork_session(session.id, "Fork")

                    self.assertNotEqual(fork.id, session.id)
                    self.assertEqual(fork.title, "Fork")
                    self.assertEqual(
                        [(message.role, message.content) for message in messages],
                        [("user", "Hallo"), ("assistant", "Hi")],
                    )
                finally:
                    controller.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_folder_system_prompt_is_used_for_new_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                config_dir = Path(tmp) / "config" / "telachat"
                config_dir.mkdir(parents=True)
                (config_dir / "config.toml").write_text(
                    """
                    default_profile = "test"
                    default_system_prompt = "Allgemein"

                    [profiles.test]
                    label = "Test"
                    base_url = "http://127.0.0.1:9/v1"
                    api_key = "test"
                    model = "demo"
                    models = ["demo", "demo-large"]

                    [profiles.other]
                    label = "Other"
                    base_url = "http://127.0.0.1:9/v1"
                    api_key = "other"
                    model = "other-default"
                    models = ["other-default"]
                    """,
                    encoding="utf-8",
                )
                controller = TelachatController()
                try:
                    folder = controller.create_folder(
                        "Projekt",
                        system_prompt="Projektkontext",
                        default_profile="test",
                        default_model="demo-large",
                    )
                    session, _messages = controller.new_session(
                        system_prompt=None,
                        folder_id=folder.id,
                    )
                    self.assertEqual(session.system_prompt, "Projektkontext")
                    self.assertEqual(session.profile, "test")
                    self.assertEqual(session.model, "demo-large")
                    explicit_same, _messages = controller.new_session(
                        profile_name="test",
                        system_prompt=None,
                        folder_id=folder.id,
                    )
                    self.assertEqual(explicit_same.profile, "test")
                    self.assertEqual(explicit_same.model, "demo-large")
                    explicit_other, _messages = controller.new_session(
                        profile_name="other",
                        system_prompt=None,
                        folder_id=folder.id,
                    )
                    self.assertEqual(explicit_other.profile, "other")
                    self.assertEqual(explicit_other.model, "other-default")
                    fallback, _messages = controller.new_session(
                        profile_name="test",
                        system_prompt=None,
                    )
                    self.assertEqual(fallback.system_prompt, "Allgemein")
                    self.assertEqual(fallback.model, "demo")
                finally:
                    controller.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_send_persists_selected_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                config_dir = Path(tmp) / "config" / "telachat"
                config_dir.mkdir(parents=True)
                (config_dir / "config.toml").write_text(
                    """
                    default_profile = "test"
                    default_system_prompt = "System"
                    max_history_messages = 8

                    [profiles.test]
                    label = "Test"
                    base_url = "http://127.0.0.1:9/v1"
                    api_key = "test"
                    model = "demo"
                    models = ["demo", "demo-large"]
                    stream = false
                    """,
                    encoding="utf-8",
                )
                controller = TelachatController()
                try:
                    with (
                        mock.patch("telachat.controller.OpenAICompatClient") as client_cls,
                        mock.patch("telachat.controller.time.perf_counter") as perf_counter,
                    ):
                        perf_counter.side_effect = [10.0, 11.25]
                        client_cls.return_value.chat.return_value = ChatResult(
                            content="Antwort",
                            raw={},
                        )
                        payload = controller.send(
                            session_id=None,
                            profile_name="test",
                            model="demo-large",
                            system_prompt="System",
                            prompt="Hallo",
                            temperature=0.45,
                            max_tokens=321,
                        )
                    selected_profile = client_cls.call_args.args[0]
                    self.assertEqual(selected_profile.temperature, 0.45)
                    self.assertEqual(selected_profile.max_tokens, 321)
                    self.assertEqual(payload.elapsed_seconds, 1.25)
                    self.assertEqual(payload.session.profile, "test")
                    self.assertEqual(payload.session.model, "demo-large")
                    stored = controller.store.get_session(payload.session.id)
                    self.assertIsNotNone(stored)
                    assert stored is not None
                    self.assertEqual(stored.model, "demo-large")
                finally:
                    controller.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
