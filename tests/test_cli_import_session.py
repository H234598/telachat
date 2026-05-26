from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from telachat.cli import main
from telachat.store import ChatStore


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


class CliImportSessionTests(unittest.TestCase):
    def test_import_session_rejects_non_utf8_json_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            import_path = Path(tmp) / "invalid-session.json"
            import_path.write_bytes(b"\xff")

            err = io.StringIO()
            with redirect_stderr(err):
                self.assertEqual(main(["import-session", str(import_path)]), 1)
            self.assertIn("nicht UTF-8-kodiert", err.getvalue())
            self.assertNotIn("Traceback", err.getvalue())

    def test_import_session_dry_run_validates_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["init"]), 0)
                import_path = Path(tmp) / "session.json"
                import_path.write_text(
                    json.dumps(
                        {
                            "format": "telachat.session.v1",
                            "session": {
                                "title": "Dry Session",
                                "profile": "openai",
                                "model": "gpt-5.5",
                                "system_prompt": "Dry system",
                            },
                            "messages": [
                                {"role": "user", "content": "Nur pruefen"},
                                {"role": "assistant", "content": "OK"},
                            ],
                        }
                    ),
                    encoding="utf-8",
                )

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(
                            [
                                "import-session",
                                str(import_path),
                                "--title",
                                "Override Dry",
                                "--folder",
                                "Ziel",
                                "--dry-run",
                                "--json",
                            ]
                        ),
                        0,
                    )
                result = json.loads(out.getvalue())
                self.assertTrue(result["dry_run"])
                self.assertEqual(result["folder"], "Ziel")
                self.assertEqual(result["messages"], 2)
                self.assertEqual(result["session"]["title"], "Override Dry")
                self.assertEqual(result["session"]["model"], "gpt-5.5")
                self.assertFalse(result["session"]["archived"])

                store = ChatStore()
                try:
                    self.assertEqual(store.list_sessions(limit=10), [])
                    self.assertEqual(store.list_folders(), [])
                finally:
                    store.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_import_session_rejects_invalid_messages_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["init"]), 0)
                import_path = Path(tmp) / "invalid.json"
                cases = [
                    (
                        [
                            {"role": "user", "content": "Schon geschrieben?"},
                            {"role": "tool", "content": "ungueltig"},
                        ],
                        "Ungueltige Importrolle",
                    ),
                    (
                        [{"role": "user", "content": {"text": "kein String"}}],
                        "Importnachricht braucht Textinhalt",
                    ),
                ]
                for messages, expected_error in cases:
                    with self.subTest(expected_error=expected_error):
                        import_path.write_text(
                            json.dumps(
                                {
                                    "format": "telachat.session.v1",
                                    "session": {"title": "Bad Import"},
                                    "messages": messages,
                                }
                            ),
                            encoding="utf-8",
                        )

                        err = io.StringIO()
                        with redirect_stderr(err):
                            self.assertEqual(main(["import-session", str(import_path)]), 1)
                        self.assertIn(expected_error, err.getvalue())

                        store = ChatStore()
                        try:
                            self.assertEqual(store.list_sessions(limit=10), [])
                        finally:
                            store.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_import_session_rejects_invalid_archived_flag_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["init"]), 0)
                import_path = Path(tmp) / "invalid-archive.json"
                import_path.write_text(
                    json.dumps(
                        {
                            "format": "telachat.session.v1",
                            "session": {"title": "Bad Archive", "archived": "yes"},
                            "messages": [{"role": "user", "content": "Nicht schreiben"}],
                        }
                    ),
                    encoding="utf-8",
                )

                err = io.StringIO()
                with redirect_stderr(err):
                    self.assertEqual(main(["import-session", str(import_path)]), 1)
                self.assertIn("Session-archived muss ein Boolean sein", err.getvalue())

                store = ChatStore()
                try:
                    self.assertEqual(store.list_sessions(limit=10, archive="all"), [])
                finally:
                    store.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)


if __name__ == "__main__":
    unittest.main()
