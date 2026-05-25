from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from telachat.cli import cli_completion_candidates, main
from telachat.config import load_config
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
                self.assertIn("Qwen/Qwen2.5-1.5B-Instruct", text)
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

    def test_folders_command_manages_system_prompts(self) -> None:
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
                    self.assertEqual(
                        main(["folders", "--create", "Projekt", "--system", "Projektkontext"]),
                        0,
                    )
                self.assertIn("Projekt", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["folders", "--set-system", "Projekt", "Nur kurz.", "--show-system"]),
                        0,
                    )
                text = out.getvalue()
                self.assertIn("system", text)
                self.assertIn("Nur kurz.", text)
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_export_folder_writes_index_and_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["init"]), 0)
                export_dir = Path(tmp) / "export"
                bundle = Path(tmp) / "bundle.md"
                store = ChatStore()
                try:
                    work = store.create_folder("Arbeit")
                    alpha = store.create_session(
                        title="Alpha Plan",
                        profile="openai",
                        system_prompt="System",
                        folder_id=work.id,
                    )
                    beta = store.create_session(
                        title="Beta Notiz",
                        profile="tki",
                        system_prompt="System",
                    )
                    store.add_message(alpha.id, "user", "Projektplan")
                    store.add_message(alpha.id, "assistant", "Antwort")
                    store.add_message(beta.id, "user", "Nicht im Export")
                finally:
                    store.close()

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["export-folder", "Arbeit", "-o", str(export_dir)]),
                        0,
                    )
                self.assertTrue((export_dir / "index.md").exists())
                exported = list(export_dir.glob("alpha-plan-*.md"))
                self.assertEqual(len(exported), 1)
                self.assertIn("Projektplan", exported[0].read_text(encoding="utf-8"))
                self.assertNotIn("Nicht im Export", (export_dir / "index.md").read_text(encoding="utf-8"))

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["export-folder", "Arbeit", "--single-file", "-o", str(bundle)]),
                        0,
                    )
                text = bundle.read_text(encoding="utf-8")
                self.assertIn("Telachat Export: Arbeit", text)
                self.assertIn("Projektplan", text)
                self.assertNotIn("Nicht im Export", text)
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

    def test_chat_command_completion_uses_context(self) -> None:
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
                    store.create_folder("Arbeit")
                    store.create_session(
                        title="Alpha Plan",
                        profile="tki",
                        system_prompt="System",
                    )
                    cfg = load_config()
                    self.assertIn("/permissions ", cli_completion_candidates("/per", cfg, store))
                    self.assertIn("openai ", cli_completion_candidates("/provider op", cfg, store))
                    self.assertIn("gpt-5.5 ", cli_completion_candidates("/model gpt", cfg, store))
                    self.assertIn("summarize ", cli_completion_candidates("/template su", cfg, store))
                    self.assertIn("Arbeit ", cli_completion_candidates("/move Ar", cfg, store))
                    self.assertIn("title ", cli_completion_candidates("/sort ti", cfg, store))
                    self.assertTrue(
                        any(
                            item.startswith("Alpha Plan")
                            for item in cli_completion_candidates("/load Alpha", cfg, store)
                        )
                    )
                finally:
                    store.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_chat_commands_cover_documented_terminal_actions(self) -> None:
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
                with redirect_stdout(out), mock.patch(
                    "builtins.input",
                    side_effect=[
                        "/provider openai",
                        "/model gpt-5.5",
                        "/move Arbeit",
                        "/rename Testtitel",
                        "/folder-system Ordnerkontext",
                        "/unfile",
                        "/sort title",
                        "/search Testtitel",
                        "/delete",
                        "/exit",
                    ],
                ):
                    self.assertEqual(main(["chat", "--no-stream"]), 0)
                text = out.getvalue()
                self.assertIn("Aktiv: openai", text)
                self.assertIn("Modell: gpt-5.5", text)
                self.assertIn("Chat abgelegt: Arbeit", text)
                self.assertIn("Umbenannt: Testtitel", text)
                self.assertIn("Ordner-Systemprompt gesetzt: Arbeit", text)
                self.assertIn("Session geloescht:", text)
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_chat_persists_selected_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["init"]), 0)

                with redirect_stdout(io.StringIO()), mock.patch(
                    "builtins.input",
                    side_effect=[
                        "/provider openai",
                        "/model gpt-5.5",
                        "Hallo",
                        "/exit",
                    ],
                ), mock.patch("telachat.cli._run_chat", return_value="Antwort"):
                    self.assertEqual(main(["chat", "--no-stream"]), 0)

                store = ChatStore()
                try:
                    sessions = store.list_sessions(10)
                    self.assertEqual(len(sessions), 1)
                    self.assertEqual(sessions[0].profile, "openai")
                    self.assertEqual(sessions[0].model, "gpt-5.5")
                    out = io.StringIO()
                    with redirect_stdout(out):
                        self.assertEqual(main(["sessions", "--query", "gpt-5.5"]), 0)
                    self.assertIn("openai/gpt-5.5", out.getvalue())
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
