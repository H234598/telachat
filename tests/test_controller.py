from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from telachat.client import ChatResult
from telachat.controller import TelachatController


class ControllerTests(unittest.TestCase):
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

                    with mock.patch("telachat.controller.OpenAICompatClient") as client_cls:
                        client_cls.return_value.chat.return_value = ChatResult(
                            content="Neu",
                            raw={},
                        )
                        payload = controller.regenerate(
                            session_id=session.id,
                            profile_name="test",
                            model="demo",
                            system_prompt="System",
                        )

                    self.assertEqual(payload.answer, "Neu")
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


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
