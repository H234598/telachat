from __future__ import annotations

import io
import json
import os
import tempfile
import tomllib
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from telachat.client import ApiError, ChatResult, TokenUsage
from telachat.cli import cli_completion_candidates, main
from telachat.config import load_config
from telachat.store import ChatStore


class CliTests(unittest.TestCase):
    def test_version_option_prints_package_version(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as raised:
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertRegex(out.getvalue(), r"^telachat \d+\.\d+\.\d+\n$")

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
                self.assertIn("huggingface", text)
                self.assertIn("TKI", text)
                self.assertNotIn("sk-", text)

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["profiles", "--json"]), 0)
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["default_profile"], "huggingface")
                self.assertTrue(
                    any(profile["name"] == "huggingface" for profile in payload["profiles"])
                )
                self.assertFalse(any(profile["name"] == "tki" for profile in payload["profiles"]))
                self.assertNotIn("sk-", out.getvalue())
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
                    store.set_session_tags(alpha.id, ["Projekt", "Review"])
                    archived = store.create_session(
                        title="Archiv Alpha",
                        profile="tki",
                        system_prompt="System",
                    )
                    store.add_message(archived.id, "user", "Archivnotiz")
                    store.set_session_archived(archived.id, True)
                finally:
                    store.close()

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["sessions", "--query", "projekt"]), 0)
                self.assertIn("Alpha", out.getvalue())
                self.assertNotIn("Beta", out.getvalue())
                self.assertNotIn("Archiv Alpha", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["sessions", "--query", "archivnotiz", "--all"]), 0)
                self.assertIn("Archiv Alpha", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["sessions", "--archived"]), 0)
                self.assertIn("Archiv Alpha", out.getvalue())
                self.assertIn("A ", out.getvalue())
                self.assertNotIn("Alpha  ", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["sessions", "--tag", "projekt"]), 0)
                self.assertIn("Alpha", out.getvalue())
                self.assertIn("#projekt", out.getvalue())
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

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["sessions", "--json", "--sort", "title"]), 0)
                payload = json.loads(out.getvalue())
                self.assertEqual(
                    [session["title"] for session in payload["sessions"]],
                    ["Beta", "Alpha"],
                )
                self.assertTrue(payload["sessions"][0]["pinned"])
                self.assertFalse(payload["sessions"][0]["archived"])
                alpha_record = next(
                    session for session in payload["sessions"] if session["title"] == "Alpha"
                )
                self.assertEqual(alpha_record["tags"], ["projekt", "review"])
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_stats_command_reports_counts_without_content(self) -> None:
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
                    folder = store.create_folder("Arbeit", system_prompt="Projektprompt")
                    session = store.create_session(
                        title="Alpha",
                        profile="openai",
                        model="gpt-5.5",
                        system_prompt="System",
                        folder_id=folder.id,
                    )
                    archived = store.create_session(
                        title="Archiv",
                        profile="tki",
                        system_prompt="System",
                    )
                    store.add_message(session.id, "user", "Geheimer Projektplan")
                    store.add_message(
                        session.id,
                        "assistant",
                        "Antwort",
                        metadata={
                            "usage": {
                                "input_tokens": 11,
                                "output_tokens": 5,
                                "total_tokens": 16,
                            }
                        },
                    )
                    store.add_message(archived.id, "user", "Archivnotiz")
                    store.set_session_pinned(session.id, True)
                    store.set_session_archived(archived.id, True)
                    store.set_session_tags(session.id, ["Projekt"])
                finally:
                    store.close()

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["stats", "--json"]), 0)
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["sessions"]["total"], 2)
                self.assertEqual(payload["sessions"]["active"], 1)
                self.assertEqual(payload["sessions"]["archived"], 1)
                self.assertEqual(payload["sessions"]["pinned"], 1)
                self.assertEqual(payload["sessions"]["unfiled"], 1)
                self.assertEqual(payload["messages"]["total"], 3)
                self.assertEqual(
                    payload["usage"],
                    {
                        "cached_input_tokens": 0,
                        "input_tokens": 11,
                        "output_tokens": 5,
                        "reasoning_tokens": 0,
                        "records": 1,
                        "total_tokens": 16,
                    },
                )
                self.assertEqual(payload["tags"]["assignments"], 1)
                self.assertEqual(payload["folders"]["with_system_prompt"], 1)
                self.assertEqual(
                    {row["profile"]: row["sessions"] for row in payload["profiles"]},
                    {"openai": 1, "tki": 1},
                )
                self.assertNotIn("Geheimer Projektplan", out.getvalue())
                self.assertNotIn("api_key", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["stats"]), 0)
                text = out.getvalue()
                self.assertIn("Sessions: 2 gesamt", text)
                self.assertIn("Nachrichten: 3 gesamt", text)
                self.assertIn("Token-Nutzung: 1 Antworten, 11 in, 5 out, 16 total", text)
                self.assertIn("Profile: openai=1, tki=1", text)
                self.assertNotIn("Geheimer Projektplan", text)

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["context", session.id, "--json"]), 0)
                context_payload = json.loads(out.getvalue())
                self.assertEqual(context_payload["messages"]["stored"], 2)
                self.assertEqual(context_payload["messages"]["next_request"], 2)
                self.assertEqual(context_payload["characters"]["system"], 6)
                self.assertGreater(context_payload["estimate"]["approx_tokens"], 0)
                self.assertNotIn("Geheimer Projektplan", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["context", session.id]), 0)
                context_text = out.getvalue()
                self.assertIn("Kontext:", context_text)
                self.assertIn("History-Limit: 24", context_text)
                self.assertNotIn("Geheimer Projektplan", context_text)
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_archive_commands_hide_and_restore_sessions(self) -> None:
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
                        title="Weglegen",
                        profile="tki",
                        system_prompt="System",
                    )
                    store.add_message(session.id, "user", "Archivtest")
                finally:
                    store.close()

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["archive", session.id, "--json"]), 0)
                payload = json.loads(out.getvalue())
                self.assertTrue(payload["session"]["archived"])

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["sessions"]), 0)
                self.assertNotIn("Weglegen", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["sessions", "--archived"]), 0)
                self.assertIn("Weglegen", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["unarchive", session.id]), 0)
                self.assertIn("Wiederhergestellt", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["sessions"]), 0)
                self.assertIn("Weglegen", out.getvalue())
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_tags_command_manages_session_tags(self) -> None:
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
                        title="Tagged",
                        profile="tki",
                        system_prompt="System",
                    )
                finally:
                    store.close()

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["tags", session.id, "--add", "Needs Review", "--add", "#Projekt"]),
                        0,
                    )
                self.assertIn("#needs-review", out.getvalue())
                self.assertIn("#projekt", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["tags", "--json"]), 0)
                payload = json.loads(out.getvalue())
                self.assertEqual(
                    [(item["tag"], item["sessions"]) for item in payload["tags"]],
                    [("needs-review", 1), ("projekt", 1)],
                )

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["tags", session.id, "--remove", "needs review", "--json"]), 0)
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["tags"], ["projekt"])
                self.assertEqual(payload["session"]["tags"], ["projekt"])
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
                with redirect_stdout(out):
                    self.assertEqual(main(["templates", "--json"]), 0)
                payload = json.loads(out.getvalue())
                summarize = next(
                    item for item in payload["templates"] if item["name"] == "summarize"
                )
                self.assertIn("preview", summarize)
                self.assertTrue(summarize["has_input_placeholder"])
                self.assertEqual(summarize["variables"], ["input"])
                self.assertGreater(summarize["characters"], 0)

                config_path = Path(os.environ["XDG_CONFIG_HOME"]) / "telachat" / "config.toml"
                config_text = config_path.read_text(encoding="utf-8")
                config_path.write_text(
                    config_text.replace(
                        "\n[profiles.",
                        '\ndaily = "Heute {date} um {time}: {input}"\n\n[profiles.',
                        1,
                    ),
                    encoding="utf-8",
                )
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["templates", "--json"]), 0)
                payload = json.loads(out.getvalue())
                daily = next(item for item in payload["templates"] if item["name"] == "daily")
                self.assertTrue(daily["has_input_placeholder"])
                self.assertEqual(daily["variables"], ["input", "date", "time"])
                self.assertEqual(daily["custom_variables"], [])

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["templates", "--show", "daily"]), 0)
                preview = out.getvalue()
                self.assertIn("Name: daily", preview)
                self.assertIn("Variablen: {input}, {date}, {time}", preview)
                self.assertIn("Heute {date} um {time}: {input}", preview)

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["templates", "--show", "daily", "--json"]), 0)
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["template"]["name"], "daily")
                self.assertEqual(payload["template"]["variables"], ["input", "date", "time"])

                config_text = config_path.read_text(encoding="utf-8")
                config_path.write_text(
                    config_text.replace(
                        "\n[profiles.",
                        '\ntriage = "Pruefe {topic} fuer {audience}: {input}"\n\n[profiles.',
                        1,
                    ),
                    encoding="utf-8",
                )
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["templates", "--show", "triage", "--json"]), 0)
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["template"]["custom_variables"], ["audience", "topic"])

                out = io.StringIO()
                with redirect_stdout(out), mock.patch(
                    "telachat.cli._run_chat",
                    return_value="OK",
                ) as run_chat:
                    self.assertEqual(
                        main(
                            [
                                "ask",
                                "--template",
                                "triage",
                                "--template-var",
                                "topic=Login",
                                "--template-var",
                                "audience=Support",
                                "--no-stream",
                                "Projektstand",
                            ]
                        ),
                        0,
                    )
                messages = run_chat.call_args.args[1]
                self.assertIn("Pruefe Login fuer Support: Projektstand", messages[-1]["content"])

                out = io.StringIO()
                err = io.StringIO()
                with redirect_stdout(out), redirect_stderr(err), mock.patch(
                    "telachat.cli._run_chat",
                    return_value="OK",
                ) as run_chat:
                    self.assertEqual(
                        main(
                            [
                                "ask",
                                "--template-var",
                                "topic=Login",
                                "--no-stream",
                                "Projektstand",
                            ]
                        ),
                        1,
                    )
                run_chat.assert_not_called()
                self.assertIn("--template-var braucht --template", err.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["templates", "--set", "brief", "Kurz: {input}", "--json"]),
                        0,
                    )
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["template"]["name"], "brief")
                self.assertEqual(payload["template"]["variables"], ["input"])
                self.assertEqual(payload["template"]["custom_variables"], [])

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["templates", "--rename", "brief", "briefing", "--json"]),
                        0,
                    )
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["renamed"], {"from": "brief", "to": "briefing"})
                self.assertEqual(payload["template"]["name"], "briefing")

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["templates", "--delete", "briefing", "--json"]), 0)
                self.assertEqual(json.loads(out.getvalue()), {"deleted": "briefing"})

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

                out = io.StringIO()
                with redirect_stdout(out), mock.patch(
                    "telachat.cli.OpenAICompatClient",
                ) as client_cls:
                    client_cls.return_value.chat.return_value = ChatResult(
                        "JSON OK",
                        {},
                        usage=TokenUsage(input_tokens=9, output_tokens=3, total_tokens=12),
                    )
                    self.assertEqual(
                        main(["ask", "--json", "--template", "summarize", "Projektstand"]),
                        0,
                    )
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["answer"], "JSON OK")
                self.assertEqual(payload["model"], "TKI")
                self.assertEqual(
                    payload["usage"],
                    {"input_tokens": 9, "output_tokens": 3, "total_tokens": 12},
                )
                self.assertEqual(client_cls.return_value.chat.call_args.kwargs["stream"], False)

                out = io.StringIO()
                err = io.StringIO()
                with redirect_stdout(out), redirect_stderr(err), mock.patch(
                    "telachat.cli.OpenAICompatClient",
                ) as client_cls:
                    client_cls.return_value.chat.return_value = ChatResult(
                        "Gespeichert",
                        {},
                        usage=TokenUsage(input_tokens=4, output_tokens=2, total_tokens=6),
                    )
                    self.assertEqual(main(["ask", "--json", "--save", "Bitte merken"]), 0)
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["answer"], "Gespeichert")
                self.assertIn("saved_session_id", payload)
                self.assertEqual(
                    payload["usage"],
                    {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
                )
                self.assertEqual("", err.getvalue())
                store = ChatStore()
                try:
                    messages = store.messages(str(payload["saved_session_id"]))
                finally:
                    store.close()
                self.assertEqual(
                    [(message.role, message.content) for message in messages],
                    [("user", "Bitte merken"), ("assistant", "Gespeichert")],
                )
                self.assertEqual(
                    messages[-1].metadata["usage"],
                    {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
                )
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
                        main(["--config", str(config), "config-check", "--json"]),
                        0,
                    )
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["app_icon"], "system")
                self.assertEqual(payload["chat_background_image"], "")
                self.assertFalse(payload["skill_watchdog_enabled"])
                self.assertEqual(payload["missing_secrets"], 1)
                profiles = {profile["name"]: profile for profile in payload["profiles"]}
                self.assertEqual(profiles["missing"]["api_key"], "env:TELACHAT_MISSING_TEST_KEY")
                self.assertNotIn("secret-value", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["--config", str(config), "config-check", "--strict"]),
                        1,
                    )

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["--config", str(config), "config-check", "--json", "--strict"]),
                        1,
                    )
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["missing_secrets"], 1)
                profiles = {profile["name"]: profile for profile in payload["profiles"]}
                self.assertFalse(profiles["missing"]["secret_ok"])
                self.assertNotIn("secret-value", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["--config", str(config), "config-check", "--profile", "ok", "--strict"]),
                        0,
                    )
                text = out.getvalue()
                self.assertIn("Profile filter: ok", text)
                self.assertIn("ok:envfile:", text)
                self.assertNotIn("missing:env:TELACHAT_MISSING_TEST_KEY", text)

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(
                            [
                                "--config",
                                str(config),
                                "config-check",
                                "--profile",
                                "missing",
                                "--json",
                                "--strict",
                            ]
                        ),
                        1,
                    )
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["profile_filter"], "missing")
                self.assertEqual(payload["missing_secrets"], 1)
                self.assertEqual([profile["name"] for profile in payload["profiles"]], ["missing"])
            finally:
                _restore_env("TELACHAT_MISSING_TEST_KEY", old_missing)

    def test_config_check_can_show_redacted_toml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            config.write_text(
                """
default_profile = "ok"

[profiles.ok]
label = "Okay"
base_url = "http://127.0.0.1:9/v1"
api_key = "sk-very-secret-123456"
model = "demo"

[profiles.ok.headers]
Authorization = "Bearer raw-token-value"
X-Trace = "visible"

[profiles.other]
label = "Other"
base_url = "http://127.0.0.1:9/v1"
api_key = "sk-other-secret-654321"
model = "other"

[profiles.other.headers]
Authorization = "Bearer other-token-value"
""".strip(),
                encoding="utf-8",
            )

            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(
                    main(["--config", str(config), "config-check", "--show-redacted"]),
                    0,
                )
            text = out.getvalue()
            self.assertIn("# Redacted Telachat config", text)
            self.assertIn("[profiles.other]", text)
            self.assertIn('api_key = "sk-...456"', text)
            self.assertIn('Authorization = "Bea...lue"', text)
            self.assertIn('X-Trace = "visible"', text)
            self.assertNotIn("very-secret", text)
            self.assertNotIn("raw-token", text)
            self.assertNotIn("other-secret", text)
            self.assertNotIn("other-token", text)
            payload = tomllib.loads(text)
            self.assertEqual(payload["profiles"]["ok"]["api_key"], "sk-...456")
            self.assertEqual(payload["profiles"]["ok"]["headers"]["X-Trace"], "visible")

            filtered = io.StringIO()
            with redirect_stdout(filtered):
                self.assertEqual(
                    main(
                        [
                            "--config",
                            str(config),
                            "config-check",
                            "--profile",
                            "ok",
                            "--show-redacted",
                        ]
                    ),
                    0,
                )
            filtered_text = filtered.getvalue()
            self.assertIn("[profiles.ok]", filtered_text)
            self.assertNotIn("[profiles.other]", filtered_text)
            filtered_payload = tomllib.loads(filtered_text)
            self.assertEqual(sorted(filtered_payload["profiles"]), ["ok"])

            err = io.StringIO()
            with redirect_stderr(err):
                self.assertEqual(
                    main(["--config", str(config), "config-check", "--json", "--show-redacted"]),
                    1,
                )
            self.assertIn("kann nicht mit --json kombiniert", err.getvalue())

    def test_models_lists_configured_and_live_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            config.write_text(
                """
default_profile = "ok"

[profiles.ok]
label = "Okay"
base_url = "http://127.0.0.1:9/v1"
api_key = "env:TELACHAT_MODELS_TEST_KEY"
model = "demo"
models = ["demo", "demo-large"]

[profiles.other]
base_url = "http://127.0.0.1:9/v1"
api_key = "env:TELACHAT_MODELS_TEST_KEY"
model = "other-model"
""".strip(),
                encoding="utf-8",
            )
            old_key = os.environ.get("TELACHAT_MODELS_TEST_KEY")
            os.environ["TELACHAT_MODELS_TEST_KEY"] = "secret-value"
            try:
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["--config", str(config), "models", "--json"]),
                        0,
                    )
                payload = json.loads(out.getvalue())
                self.assertFalse(payload["live"])
                self.assertIsNone(payload["profile_filter"])
                self.assertEqual(
                    [profile["name"] for profile in payload["profiles"]],
                    ["ok", "other"],
                )
                self.assertEqual(
                    payload["profiles"][0]["configured_models"],
                    ["demo", "demo-large"],
                )
                self.assertNotIn("secret-value", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out), mock.patch(
                    "telachat.cli.OpenAICompatClient",
                ) as client_cls:
                    client_cls.return_value.list_models.return_value = [
                        "live-demo",
                        "live-large",
                    ]
                    self.assertEqual(
                        main(
                            [
                                "--config",
                                str(config),
                                "models",
                                "--profile",
                                "ok",
                                "--live",
                                "--json",
                            ]
                        ),
                        0,
                    )
                payload = json.loads(out.getvalue())
                self.assertTrue(payload["live"])
                self.assertEqual(payload["profile_filter"], "ok")
                self.assertEqual(
                    payload["profiles"][0]["live_models"],
                    ["live-demo", "live-large"],
                )
                self.assertEqual(client_cls.call_args.args[0].name, "ok")
                self.assertNotIn("secret-value", out.getvalue())
            finally:
                _restore_env("TELACHAT_MODELS_TEST_KEY", old_key)

    def test_doctor_json_reports_live_checks_without_leaking_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            _write_doctor_test_config(config)
            old_key = os.environ.get("TELACHAT_DOCTOR_TEST_KEY")
            os.environ["TELACHAT_DOCTOR_TEST_KEY"] = "secret-value"
            try:
                out = io.StringIO()
                with redirect_stdout(out), mock.patch(
                    "telachat.cli.OpenAICompatClient",
                ) as client_cls:
                    client_cls.return_value.list_models.return_value = ["demo"]
                    client_cls.return_value.chat.return_value = ChatResult(
                        "OK",
                        {},
                        usage=TokenUsage(
                            input_tokens=4,
                            output_tokens=2,
                            total_tokens=6,
                        ),
                    )
                    self.assertEqual(
                        main(["--config", str(config), "doctor", "--json", "--chat"]),
                        0,
                    )
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["checks"]["models"]["models"], ["demo"])
                self.assertEqual(payload["checks"]["chat"]["preview"], "OK")
                self.assertEqual(
                    payload["checks"]["chat"]["usage"],
                    {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
                )
                self.assertEqual(payload["profile"]["api_key"], "env:TELACHAT_DOCTOR_TEST_KEY")
                self.assertNotIn("secret-value", out.getvalue())
            finally:
                _restore_env("TELACHAT_DOCTOR_TEST_KEY", old_key)

    def test_doctor_json_without_chat_skips_chat_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            _write_doctor_test_config(config)
            old_key = os.environ.get("TELACHAT_DOCTOR_TEST_KEY")
            os.environ["TELACHAT_DOCTOR_TEST_KEY"] = "secret-value"
            try:
                out = io.StringIO()
                with redirect_stdout(out), mock.patch(
                    "telachat.cli.OpenAICompatClient",
                ) as client_cls:
                    client_cls.return_value.list_models.return_value = ["demo"]
                    self.assertEqual(
                        main(["--config", str(config), "doctor", "--json"]),
                        0,
                    )
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["checks"]["models"]["models"], ["demo"])
                self.assertIsNone(payload["checks"]["chat"])
                client_cls.return_value.chat.assert_not_called()
                self.assertNotIn("secret-value", out.getvalue())
            finally:
                _restore_env("TELACHAT_DOCTOR_TEST_KEY", old_key)

    def test_doctor_text_reports_models_before_chat_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            _write_doctor_test_config(config)
            old_key = os.environ.get("TELACHAT_DOCTOR_TEST_KEY")
            os.environ["TELACHAT_DOCTOR_TEST_KEY"] = "secret-value"
            try:
                out = io.StringIO()
                err = io.StringIO()
                with redirect_stdout(out), redirect_stderr(err), mock.patch(
                    "telachat.cli.OpenAICompatClient",
                ) as client_cls:
                    client_cls.return_value.list_models.return_value = ["demo"]
                    client_cls.return_value.chat.side_effect = ApiError("Chat kaputt")
                    self.assertEqual(
                        main(["--config", str(config), "doctor", "--chat"]),
                        1,
                    )
                self.assertIn("/models: ok (demo)", out.getvalue())
                self.assertIn("Fehler: Chat kaputt", err.getvalue())
                self.assertNotIn("secret-value", out.getvalue())
            finally:
                _restore_env("TELACHAT_DOCTOR_TEST_KEY", old_key)

    def test_doctor_text_reports_profile_before_models_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            _write_doctor_test_config(config)
            old_key = os.environ.get("TELACHAT_DOCTOR_TEST_KEY")
            os.environ["TELACHAT_DOCTOR_TEST_KEY"] = "secret-value"
            try:
                out = io.StringIO()
                err = io.StringIO()
                with redirect_stdout(out), redirect_stderr(err), mock.patch(
                    "telachat.cli.OpenAICompatClient",
                ) as client_cls:
                    client_cls.return_value.list_models.side_effect = ApiError("Models kaputt")
                    self.assertEqual(
                        main(["--config", str(config), "doctor"]),
                        1,
                    )
                self.assertIn("Profil: ok (ok)", out.getvalue())
                self.assertIn("API-Key: env:TELACHAT_DOCTOR_TEST_KEY", out.getvalue())
                self.assertIn("Fehler: Models kaputt", err.getvalue())
                self.assertNotIn("secret-value", out.getvalue())
            finally:
                _restore_env("TELACHAT_DOCTOR_TEST_KEY", old_key)

    def test_doctor_reports_secret_source_errors_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            missing_envfile = Path(tmp) / "missing.env"
            config.write_text(
                f"""
default_profile = "broken"

[profiles.broken]
label = "Broken"
base_url = "http://127.0.0.1:9/v1"
api_key = "envfile:{missing_envfile}#TELACHAT_TEST_KEY"
model = "demo"
stream = false
""".strip(),
                encoding="utf-8",
            )

            out = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(main(["--config", str(config), "doctor"]), 1)

            self.assertIn("Profil: broken", out.getvalue())
            self.assertIn("Fehler:", err.getvalue())
            self.assertIn("missing.env", err.getvalue())
            self.assertNotIn("Traceback", err.getvalue())

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
                self.assertIn("Header validation: on", out.getvalue())
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_skill_watchdog_command_compacts_oversized_descriptions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "plugin" / "skills" / "demo" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "---\nname: demo\ndescription: |\n  "
                + ("x" * 1100)
                + "\n---\n# Demo\n",
                encoding="utf-8",
            )

            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(
                    main(["skill-watchdog", "--root", str(Path(tmp)), "--json"]),
                    0,
                )

            payload = json.loads(out.getvalue())
            self.assertEqual(payload["compacted"], 1)
            self.assertEqual(payload["errors"], [])
            self.assertIn("Telachat-safe", skill.read_text(encoding="utf-8"))

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
                        main(
                            [
                                "folders",
                                "--create",
                                "Projekt",
                                "--system",
                                "Projektkontext",
                                "--profile",
                                "tki",
                                "--model",
                                "qwen-folder",
                            ]
                        ),
                        0,
                    )
                self.assertIn("Projekt", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["folders", "--set-backend", "Projekt", "tki", "qwen-alt"]),
                        0,
                    )
                self.assertIn("Default-Backend gesetzt", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["folders", "--set-system", "Projekt", "Nur kurz.", "--show-system"]),
                        0,
                    )
                text = out.getvalue()
                self.assertIn("system", text)
                self.assertIn("Nur kurz.", text)

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["folders", "--json"]), 0)
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["folders"][0]["name"], "Projekt")
                self.assertTrue(payload["folders"][0]["has_system_prompt"])
                self.assertTrue(payload["folders"][0]["has_default_backend"])
                self.assertEqual(payload["folders"][0]["default_profile"], "huggingface")
                self.assertEqual(payload["folders"][0]["default_model"], "qwen-alt")
                self.assertNotIn("system_prompt", payload["folders"][0])

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["folders", "--json", "--show-system"]), 0)
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["folders"][0]["name"], "Projekt")
                self.assertEqual(payload["folders"][0]["system_prompt"], "Nur kurz.")

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["folders", "--clear-backend", "Projekt"]), 0)
                self.assertIn("Default-Backend geloescht", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["folders", "--json"]), 0)
                payload = json.loads(out.getvalue())
                self.assertFalse(payload["folders"][0]["has_default_backend"])
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
                folder_json = Path(tmp) / "folder.json"
                store = ChatStore()
                try:
                    work = store.create_folder(
                        "Arbeit",
                        system_prompt="Projektprompt",
                        default_profile="tki",
                        default_model="qwen-folder",
                    )
                    store.create_folder("Leer")
                    alpha = store.create_session(
                        title="Alpha Plan",
                        profile="openai",
                        model="gpt-5.5",
                        system_prompt="System",
                        folder_id=work.id,
                    )
                    archived = store.create_session(
                        title="Gamma Archiv",
                        profile="tki",
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
                    store.add_message(archived.id, "user", "Archivierter Projektplan")
                    store.set_session_archived(archived.id, True)
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
                self.assertNotIn("gamma-archiv", "\n".join(path.name for path in export_dir.iterdir()))

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["export-folder", "Arbeit", "--single-file", "-o", str(bundle)]),
                        0,
                    )
                text = bundle.read_text(encoding="utf-8")
                self.assertIn("Telachat Export: Arbeit", text)
                self.assertIn("Projektplan", text)
                self.assertNotIn("Archivierter Projektplan", text)
                self.assertNotIn("Nicht im Export", text)

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["export-folder", "Arbeit", "--json", "-o", str(folder_json)]),
                        0,
                    )
                self.assertEqual(out.getvalue().strip(), str(folder_json))
                payload = json.loads(folder_json.read_text(encoding="utf-8"))
                self.assertEqual(payload["format"], "telachat.folder.v1")
                self.assertEqual(payload["title"], "Arbeit")
                self.assertEqual(payload["folder"]["kind"], "folder")
                self.assertEqual(payload["folder"]["name"], "Arbeit")
                self.assertEqual(payload["folder"]["system_prompt"], "Projektprompt")
                self.assertEqual(payload["folder"]["default_profile"], "tki")
                self.assertEqual(payload["folder"]["default_model"], "qwen-folder")
                self.assertEqual(payload["sessions"][0]["session"]["title"], "Alpha Plan")
                self.assertEqual(payload["sessions"][0]["session"]["model"], "gpt-5.5")
                self.assertEqual(payload["sessions"][0]["session"]["system_prompt"], "System")
                self.assertEqual(
                    [(message["role"], message["content"]) for message in payload["sessions"][0]["messages"]],
                    [("user", "Projektplan"), ("assistant", "Antwort")],
                )
                encoded = json.dumps(payload, sort_keys=True)
                self.assertNotIn("Archivierter Projektplan", encoded)
                self.assertNotIn("Nicht im Export", encoded)
                self.assertNotIn("api_key", encoded)

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["export-folder", "Arbeit", "--archived", "--json"]),
                        0,
                    )
                archived_payload = json.loads(out.getvalue())
                self.assertEqual(
                    [item["session"]["title"] for item in archived_payload["sessions"]],
                    ["Gamma Archiv"],
                )
                self.assertTrue(archived_payload["sessions"][0]["session"]["archived"])

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["export-folder", "Arbeit", "--all", "--json"]), 0)
                all_payload = json.loads(out.getvalue())
                self.assertEqual(
                    [item["session"]["title"] for item in all_payload["sessions"]],
                    ["Alpha Plan", "Gamma Archiv"],
                )

                err = io.StringIO()
                with redirect_stderr(err):
                    self.assertEqual(main(["export-folder", "Arbeit", "--archived", "--all"]), 1)
                self.assertIn("--archived und --all schliessen sich aus", err.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["export-folder", "Leer", "--json"]), 0)
                empty = json.loads(out.getvalue())
                self.assertEqual(empty["folder"]["name"], "Leer")
                self.assertEqual(empty["sessions"], [])
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_export_session_json_writes_structured_messages(self) -> None:
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
                        title="JSON Export",
                        profile="openai",
                        model="gpt-5.5",
                        system_prompt="System JSON",
                    )
                    store.set_session_tags(session.id, ["json tag"])
                    store.set_session_archived(session.id, True)
                    store.add_message(session.id, "user", "Hallo JSON")
                    store.add_message(session.id, "assistant", "Antwort JSON")
                finally:
                    store.close()

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["export", session.id, "--json"]), 0)
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["format"], "telachat.session.v1")
                self.assertEqual(payload["session"]["title"], "JSON Export")
                self.assertEqual(payload["session"]["model"], "gpt-5.5")
                self.assertEqual(payload["session"]["system_prompt"], "System JSON")
                self.assertTrue(payload["session"]["archived"])
                self.assertEqual(payload["session"]["tags"], ["json-tag"])
                self.assertEqual(
                    [(item["role"], item["content"]) for item in payload["messages"]],
                    [("user", "Hallo JSON"), ("assistant", "Antwort JSON")],
                )
                self.assertNotIn("secret-value", out.getvalue())

                target = Path(tmp) / "session.json"
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["export", session.id, "--json", "-o", str(target)]), 0)
                self.assertEqual(out.getvalue().strip(), str(target))
                self.assertEqual(
                    json.loads(target.read_text(encoding="utf-8"))["messages"][0]["content"],
                    "Hallo JSON",
                )

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(
                            [
                                "import-session",
                                str(target),
                                "--title",
                                "Import JSON",
                                "--folder",
                                "Importe",
                                "--json",
                            ]
                        ),
                        0,
                    )
                imported = json.loads(out.getvalue())
                self.assertEqual(imported["messages"], 2)
                self.assertEqual(imported["imported"]["title"], "Import JSON")
                store = ChatStore()
                try:
                    imported_session = store.get_session(imported["imported"]["id"])
                    self.assertIsNotNone(imported_session)
                    self.assertEqual(imported_session.model, "gpt-5.5")
                    self.assertTrue(imported_session.archived)
                    self.assertEqual(imported_session.tags, ("json-tag",))
                    self.assertEqual(
                        [(message.role, message.content) for message in store.messages(imported_session.id)],
                        [("user", "Hallo JSON"), ("assistant", "Antwort JSON")],
                    )
                    self.assertEqual(store.get_folder(imported_session.folder_id).name, "Importe")
                finally:
                    store.close()
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
Cookie = "session=super-secret-value"
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
                    parsed["profiles"]["local-profile"]["headers"]["Cookie"],
                    "ses...lue",
                )
                self.assertEqual(
                    parsed["profiles"]["local-profile"]["headers"]["X-Test-Header"],
                    "yes",
                )
                self.assertEqual(manifest["counts"]["sessions"], 1)
                self.assertEqual(manifest["counts"]["messages"], 1)
                self.assertEqual(manifest["theme"], "system")
                self.assertEqual(manifest["app_icon"], "system")
                self.assertEqual(manifest["chat_background_image"], "")
                self.assertTrue(manifest["validate_profile_headers"])
                self.assertFalse(manifest["skill_watchdog_enabled"])
                self.assertEqual(parsed["theme"], "system")
                self.assertEqual(parsed["app_icon"], "system")
                self.assertEqual(parsed["chat_background_image"], "")
                self.assertTrue(parsed["validate_profile_headers"])
                self.assertFalse(parsed["skill_watchdog_enabled"])

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

    def test_fork_command_and_chat_slash_fork_copy_history(self) -> None:
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
                        title="Fork original",
                        profile="tki",
                        system_prompt="System",
                    )
                    store.add_message(session.id, "user", "Hallo")
                    store.add_message(session.id, "assistant", "Hi")
                finally:
                    store.close()

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["fork", session.id, "--title", "Fork per CLI"]),
                        0,
                    )
                self.assertIn("Fork per CLI", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out), mock.patch(
                    "builtins.input",
                    side_effect=["/fork Fork per Slash", "/find hallo", "/history 4", "/exit"],
                ):
                    self.assertEqual(main(["chat", "--session", session.id, "--no-stream"]), 0)
                self.assertIn("Fork geladen:", out.getvalue())
                self.assertIn("Fork per Slash", out.getvalue())
                self.assertIn("Treffer:", out.getvalue())
                self.assertIn("1. Du: Hallo", out.getvalue())
                self.assertIn("Du> Hallo", out.getvalue())
                store = ChatStore()
                try:
                    sessions = store.list_sessions(10, sort="title_asc")
                    self.assertEqual(
                        sorted(session.title for session in sessions),
                        ["Fork original", "Fork per CLI", "Fork per Slash"],
                    )
                    for item in sessions:
                        self.assertEqual(
                            [
                                (message.role, message.content)
                                for message in store.messages(item.id)
                            ],
                            [("user", "Hallo"), ("assistant", "Hi")],
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
                    session = store.create_session(
                        title="Alpha Plan",
                        profile="tki",
                        system_prompt="System",
                    )
                    store.set_session_tags(session.id, ["Projekt"])
                    cfg = load_config()
                    self.assertIn("/permissions ", cli_completion_candidates("/per", cfg, store))
                    self.assertIn("/archive ", cli_completion_candidates("/ar", cfg, store))
                    self.assertIn("openai ", cli_completion_candidates("/provider op", cfg, store))
                    self.assertIn("gpt-5.5 ", cli_completion_candidates("/model gpt", cfg, store))
                    self.assertIn("live ", cli_completion_candidates("/models li", cfg, store))
                    self.assertIn("summarize ", cli_completion_candidates("/template su", cfg, store))
                    self.assertIn("dracula ", cli_completion_candidates("/theme dr", cfg, store))
                    self.assertIn("Arbeit ", cli_completion_candidates("/move Ar", cfg, store))
                    self.assertIn("projekt ", cli_completion_candidates("/tag pr", cfg, store))
                    self.assertIn("title ", cli_completion_candidates("/sort ti", cfg, store))
                    self.assertTrue(
                        any(
                            item.startswith("Alpha Plan")
                            for item in cli_completion_candidates("/load Alpha", cfg, store)
                        )
                    )
                    store.set_session_archived(session.id, True)
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
                        "/models",
                        "/models live",
                        "/shortcuts",
                        "/model gpt-5.5",
                        "/doctor",
                        "/theme dracula",
                        "/theme",
                        "/move Arbeit",
                        "/rename Testtitel",
                        "/archive",
                        "/archives",
                        "/unarchive",
                        "/tag Projekt Review",
                        "/tags",
                        "/stats",
                        "/untag Review",
                        "/folder-system Ordnerkontext",
                        "/unfile",
                        "/sort title",
                        "/search Testtitel",
                        "/delete",
                        "/exit",
                    ],
                ), mock.patch("telachat.cli.OpenAICompatClient") as client_cls:
                    client_cls.return_value.list_models.return_value = ["gpt-test"]
                    self.assertEqual(main(["chat", "--no-stream"]), 0)
                text = out.getvalue()
                self.assertIn("Aktiv: openai", text)
                self.assertIn("/models: configured (gpt-5.5", text)
                self.assertIn("/models: live (gpt-test)", text)
                self.assertIn("Shift+Enter", text)
                self.assertIn("Modell: gpt-5.5", text)
                self.assertIn("/models: ok (gpt-test)", text)
                self.assertIn("Theme gesetzt: dracula", text)
                self.assertIn("Aktives Theme: dracula", text)
                self.assertIn("Chat abgelegt: Arbeit", text)
                self.assertIn("Umbenannt: Testtitel", text)
                self.assertIn("Session archiviert.", text)
                self.assertIn("Session wiederhergestellt.", text)
                self.assertIn("Tags: #projekt #review", text)
                self.assertIn("#projekt  1", text)
                self.assertIn("Nachrichten: 0 gesamt", text)
                self.assertIn("Tags: #projekt", text)
                self.assertIn("Ordner-Systemprompt gesetzt: Arbeit", text)
                self.assertIn("Session geloescht:", text)
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_chat_doctor_command_reports_secret_source_errors_without_exiting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                config_dir = Path(tmp) / "config" / "telachat"
                config_dir.mkdir(parents=True)
                missing_envfile = config_dir / "missing.env"
                (config_dir / "config.toml").write_text(
                    f"""
default_profile = "broken"

[profiles.broken]
label = "Broken"
base_url = "http://127.0.0.1:9/v1"
api_key = "envfile:{missing_envfile}#TELACHAT_TEST_KEY"
model = "demo"
stream = false
""".strip(),
                    encoding="utf-8",
                )

                out = io.StringIO()
                err = io.StringIO()
                with (
                    redirect_stdout(out),
                    redirect_stderr(err),
                    mock.patch("builtins.input", side_effect=["/doctor", "/exit"]),
                ):
                    self.assertEqual(main(["chat", "--no-stream"]), 0)

                self.assertIn("Neue Session", out.getvalue())
                self.assertIn("/models: Fehler", err.getvalue())
                self.assertIn("missing.env", err.getvalue())
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_chat_send_reports_secret_source_errors_without_exiting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                config_dir = Path(tmp) / "config" / "telachat"
                config_dir.mkdir(parents=True)
                missing_envfile = config_dir / "missing.env"
                (config_dir / "config.toml").write_text(
                    f"""
default_profile = "broken"

[profiles.broken]
label = "Broken"
base_url = "http://127.0.0.1:9/v1"
api_key = "envfile:{missing_envfile}#TELACHAT_TEST_KEY"
model = "demo"
stream = false
""".strip(),
                    encoding="utf-8",
                )

                err = io.StringIO()
                with (
                    redirect_stdout(io.StringIO()),
                    redirect_stderr(err),
                    mock.patch("builtins.input", side_effect=["Hallo", "/exit"]),
                ):
                    self.assertEqual(main(["chat", "--no-stream"]), 0)

                self.assertIn("Fehler:", err.getvalue())
                self.assertIn("missing.env", err.getvalue())
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_chat_theme_command_rejects_unknown_theme_without_changing_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["init"]), 0)
                    self.assertEqual(main(["theme", "dark"]), 0)

                out = io.StringIO()
                err = io.StringIO()
                with redirect_stdout(out), redirect_stderr(err), mock.patch(
                    "builtins.input",
                    side_effect=["/theme neon", "/theme", "/exit"],
                ):
                    self.assertEqual(main(["chat", "--no-stream"]), 0)

                self.assertIn("Fehler: Unbekanntes Theme 'neon'", err.getvalue())
                self.assertIn("Aktives Theme: dark", out.getvalue())
                self.assertEqual(load_config().theme, "dark")
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_chat_find_command_searches_current_session_messages(self) -> None:
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
                        title="Find",
                        profile="tki",
                        system_prompt="System",
                    )
                    store.add_message(session.id, "user", "Bitte die Alpha-Notiz merken")
                    store.add_message(session.id, "assistant", "Alpha ist gespeichert")
                finally:
                    store.close()

                out = io.StringIO()
                with redirect_stdout(out), mock.patch(
                    "builtins.input",
                    side_effect=["/find alpha", "/find zeta", "/find", "/exit"],
                ):
                    self.assertEqual(main(["chat", "--session", session.id, "--no-stream"]), 0)

                text = out.getvalue()
                self.assertIn("Treffer:", text)
                self.assertIn("1. Du: Bitte die Alpha-Notiz merken", text)
                self.assertIn("2. KI: Alpha ist gespeichert", text)
                self.assertIn("Keine Treffer in der aktuellen Unterhaltung.", text)
                self.assertIn("Nutzung: /find TEXT", text)
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


def _write_doctor_test_config(path: Path) -> None:
    path.write_text(
        """
default_profile = "ok"

[profiles.ok]
base_url = "http://127.0.0.1:9/v1"
api_key = "env:TELACHAT_DOCTOR_TEST_KEY"
model = "demo"
""".strip(),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
