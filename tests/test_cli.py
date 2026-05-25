from __future__ import annotations

import io
import json
import os
import tempfile
import tomllib
import unittest
import zipfile
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

    def test_config_check_redacts_and_supports_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            envfile = Path(tmp) / "ok.env"
            envfile.write_text("TELACHAT_TEST_KEY=secret-value\n", encoding="utf-8")
            config = Path(tmp) / "config.toml"
            config.write_text(
                f"""
default_profile = "ok"

[profiles.ok]
base_url = "http://127.0.0.1:9/v1"
api_key = "envfile:{envfile}#TELACHAT_TEST_KEY"
model = "demo"

[profiles.missing]
base_url = "http://127.0.0.1:9/v1"
api_key = "env:TELACHAT_MISSING_TEST_KEY"
model = "demo"
""".strip(),
                encoding="utf-8",
            )
            old_missing = os.environ.get("TELACHAT_MISSING_TEST_KEY")
            os.environ.pop("TELACHAT_MISSING_TEST_KEY", None)
            try:
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["--config", str(config), "config-check"]), 0)
                text = out.getvalue()
                self.assertIn("ok:envfile:", text)
                self.assertIn("missing:env:TELACHAT_MISSING_TEST_KEY", text)
                self.assertNotIn("secret-value", text)

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["--config", str(config), "config-check", "--strict"]),
                        1,
                    )
            finally:
                _restore_env("TELACHAT_MISSING_TEST_KEY", old_missing)

    def test_theme_command_sets_configured_theme(self) -> None:
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
                    self.assertEqual(main(["theme", "dark"]), 0)
                self.assertIn("Theme gesetzt: dark", out.getvalue())
                self.assertIn("* dark", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["config-check"]), 0)
                self.assertIn("Theme: dark", out.getvalue())
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

    def test_backup_writes_redacted_config_manifest_and_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            old_state = os.environ.get("XDG_STATE_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            os.environ["XDG_STATE_HOME"] = str(Path(tmp) / "state")
            try:
                config_dir = Path(tmp) / "config" / "telachat"
                config_dir.mkdir(parents=True)
                envfile = config_dir / "secret.env"
                envfile.write_text("TELACHAT_TEST_KEY=super-secret-value\n", encoding="utf-8")
                (config_dir / "config.toml").write_text(
                    f"""
                default_profile = "local-profile"
                default_system_prompt = "System"

[prompt_templates]
quick-note = "Summarize"

[profiles.local-profile]
label = "Local"
base_url = "http://127.0.0.1:9/v1"
api_key = "envfile:{envfile}#TELACHAT_TEST_KEY"
model = "demo"
models = ["demo", "demo-large"]

[profiles.local-profile.headers]
Authorization = "Bearer super-secret-value"
X-Test-Header = "yes"
""".strip(),
                    encoding="utf-8",
                )
                store = ChatStore()
                try:
                    session = store.create_session(
                        title="Backup",
                        profile="local-profile",
                        model="demo-large",
                        system_prompt="System",
                    )
                    store.add_message(session.id, "user", "Hallo Backup")
                finally:
                    store.close()

                output_dir = Path(tmp) / "backup"
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["backup", "-o", str(output_dir)]), 0)
                backup_path = Path(out.getvalue().strip())
                self.assertTrue(backup_path.exists())
                self.assertEqual(backup_path.parent, output_dir)
                with zipfile.ZipFile(backup_path) as archive:
                    names = set(archive.namelist())
                    self.assertEqual(names, {"history.sqlite3", "config.redacted.toml", "manifest.json"})
                    redacted = archive.read("config.redacted.toml").decode("utf-8")
                    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                self.assertIn("envfile:", redacted)
                self.assertNotIn("super-secret-value", redacted)
                self.assertNotIn("super-secret-value", json.dumps(manifest))
                parsed = tomllib.loads(redacted)
                self.assertEqual(parsed["prompt_templates"]["quick-note"], "Summarize")
                self.assertEqual(
                    parsed["profiles"]["local-profile"]["headers"]["Authorization"],
                    "Bea...lue",
                )
                self.assertEqual(
                    parsed["profiles"]["local-profile"]["headers"]["X-Test-Header"],
                    "yes",
                )
                self.assertEqual(manifest["counts"]["sessions"], 1)
                self.assertEqual(manifest["counts"]["messages"], 1)
                self.assertEqual(manifest["theme"], "system")
                self.assertEqual(parsed["theme"], "system")

                restore_data = Path(tmp) / "restore-data"
                os.environ["XDG_DATA_HOME"] = str(restore_data)
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["restore", "--dry-run", str(backup_path)]), 0)
                self.assertIn("Wuerde importieren: 1 Sessions, 1 Nachrichten", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["restore", str(backup_path)]), 0)
                self.assertIn("Importiert: 1 Sessions, 1 Nachrichten", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["import-backup", str(backup_path)]), 0)
                self.assertIn("Importiert: 1 Sessions, 1 Nachrichten", out.getvalue())

                target_store = ChatStore()
                try:
                    sessions = target_store.list_sessions(limit=10, folder_id="__all__")
                    self.assertEqual(len(sessions), 2)
                    self.assertEqual({session.title for session in sessions}, {"Backup"})
                    self.assertEqual(
                        {message.content for session in sessions for message in target_store.messages(session.id)},
                        {"Hallo Backup"},
                    )
                    self.assertEqual(len({session.id for session in sessions}), 2)
                finally:
                    target_store.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)
                _restore_env("XDG_STATE_HOME", old_state)

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

    def test_chat_edit_last_command_replaces_user_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["init"]), 0)
                store = ChatStore()
                try:
                    session = store.create_session(
                        title="Edit",
                        profile="tki",
                        system_prompt="System",
                    )
                    store.add_message(session.id, "user", "Alt")
                    store.add_message(session.id, "assistant", "Antwort")
                finally:
                    store.close()

                out = io.StringIO()
                with redirect_stdout(out), mock.patch(
                    "builtins.input",
                    side_effect=["/edit Neu formuliert", "/exit"],
                ):
                    self.assertEqual(main(["chat", "--session", session.id, "--no-stream"]), 0)

                self.assertIn("Letzte Nutzernachricht aktualisiert", out.getvalue())
                store = ChatStore()
                try:
                    self.assertEqual(
                        [(message.role, message.content) for message in store.messages(session.id)],
                        [("user", "Neu formuliert")],
                    )
                finally:
                    store.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_chat_edit_last_then_regenerate_uses_updated_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["init"]), 0)
                store = ChatStore()
                try:
                    session = store.create_session(
                        title="Edit Regen",
                        profile="tki",
                        system_prompt="System",
                    )
                    store.add_message(session.id, "user", "Alt")
                    store.add_message(session.id, "assistant", "Antwort")
                finally:
                    store.close()

                with redirect_stdout(io.StringIO()), mock.patch(
                    "builtins.input",
                    side_effect=["/edit Neu formuliert", "/regen", "/exit"],
                ), mock.patch("telachat.cli._run_chat", return_value="Neue Antwort") as run_chat:
                    self.assertEqual(main(["chat", "--session", session.id, "--no-stream"]), 0)

                messages_for_chat = run_chat.call_args.args[1]
                self.assertEqual(messages_for_chat[-1]["content"], "Neu formuliert")
                store = ChatStore()
                try:
                    self.assertEqual(
                        [(message.role, message.content) for message in store.messages(session.id)],
                        [("user", "Neu formuliert"), ("assistant", "Neue Antwort")],
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
