from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from telachat.cli import main
from telachat.store import ChatStore


class CliTests(unittest.TestCase):
    def test_init_and_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["init"]), 0)
                self.assertIn("Konfiguration bereit", out.getvalue())
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["profiles"]), 0)
                text = out.getvalue()
                self.assertIn("tki", text)
                self.assertIn("gpt-4", text)
                self.assertNotIn("sk-", text)
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_sessions_can_filter_search_and_sort(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["init"]), 0)
                store = ChatStore()
                try:
                    work = store.create_folder("Arbeit")
                    alpha = store.create_session(
                        title="Alpha",
                        profile="openai",
                        system_prompt="System",
                        folder_id=work.id,
                    )
                    beta = store.create_session(
                        title="Beta",
                        profile="tki",
                        system_prompt="System",
                    )
                    store.add_message(alpha.id, "user", "Projektplan")
                    store.add_message(beta.id, "user", "Notiz")
                    store.set_session_pinned(beta.id, True)
                finally:
                    store.close()

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["sessions", "--query", "projekt"]), 0)
                self.assertIn("Alpha", out.getvalue())
                self.assertNotIn("Beta", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["sessions", "--folder", "Arbeit"]), 0)
                self.assertIn("Alpha", out.getvalue())
                self.assertNotIn("Beta", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["sessions", "--sort", "title"]), 0)
                text = out.getvalue()
                self.assertLess(text.index("Beta"), text.index("Alpha"))
                self.assertIn("* ", text)
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_templates_command_and_ask_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["init"]), 0)

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["templates"]), 0)
                self.assertIn("summarize", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out), mock.patch(
                    "telachat.cli._run_chat",
                    return_value="OK",
                ) as run_chat:
                    self.assertEqual(
                        main(["ask", "--template", "summarize", "--no-stream", "Projektstand"]),
                        0,
                    )
                messages = run_chat.call_args.args[1]
                self.assertIn("Projektstand", messages[-1]["content"])
                self.assertIn("Fasse", messages[-1]["content"])
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_chat_regenerate_command_replaces_last_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["init"]), 0)
                store = ChatStore()
                try:
                    session = store.create_session(
                        title="Regenerate",
                        profile="tki",
                        system_prompt="System",
                    )
                    store.add_message(session.id, "user", "Hallo")
                    store.add_message(session.id, "assistant", "Alt")
                finally:
                    store.close()

                out = io.StringIO()
                with redirect_stdout(out), mock.patch(
                    "builtins.input",
                    side_effect=["/regen", "/exit"],
                ), mock.patch("telachat.cli._run_chat", return_value="Neu"):
                    self.assertEqual(main(["chat", "--session", session.id, "--no-stream"]), 0)

                store = ChatStore()
                try:
                    self.assertEqual(
                        [(message.role, message.content) for message in store.messages(session.id)],
                        [("user", "Hallo"), ("assistant", "Neu")],
                    )
                finally:
                    store.close()
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
