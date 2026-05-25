from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from telachat.cli import main
from telachat.store import ChatStore, normalize_tag


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


class TagEdgeTests(unittest.TestCase):
    def test_tags_for_session_and_delete_cascade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChatStore(Path(tmp) / "history.sqlite3")
            try:
                session = store.create_session(
                    title="Taggable",
                    profile="openai",
                    model="gpt-5.5",
                    system_prompt="System",
                )
                self.assertEqual(normalize_tag("  #Projekt  Plan  "), "projekt-plan")
                with self.assertRaisesRegex(ValueError, "Tag fehlt"):
                    normalize_tag("###")

                store.set_session_tags(session.id, ["#Projekt Plan", "Review"])
                self.assertEqual(store.tags_for_session(session.id), ["projekt-plan", "review"])
                self.assertEqual(store.list_tags(), [("projekt-plan", 1), ("review", 1)])

                store.delete_session(session.id)
                self.assertEqual(store.list_tags(), [])
                with self.assertRaises(KeyError):
                    store.tags_for_session(session.id)
            finally:
                store.close()

    def test_import_session_rejects_invalid_tags_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["init"]), 0)
                import_path = Path(tmp) / "invalid-tags.json"
                cases = [
                    ("not-a-list", "Session-Tags muessen eine Liste sein."),
                    (["ok", "###"], "Tag fehlt."),
                ]
                for tags, expected_error in cases:
                    with self.subTest(expected_error=expected_error):
                        import_path.write_text(
                            json.dumps(
                                {
                                    "format": "telachat.session.v1",
                                    "session": {"title": "Bad Tags", "tags": tags},
                                    "messages": [{"role": "user", "content": "Soll nicht schreiben"}],
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

    def test_tags_command_rejects_conflicting_mutations_without_changing_tags(self) -> None:
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
                        title="Conflicting Tags",
                        profile="tki",
                        system_prompt="System",
                    )
                    store.set_session_tags(session.id, ["keep"])
                finally:
                    store.close()

                err = io.StringIO()
                with redirect_stderr(err):
                    self.assertEqual(
                        main(["tags", session.id, "--clear", "--add", "drop"]),
                        1,
                    )
                self.assertIn("kann nicht mit --add/--remove kombiniert werden", err.getvalue())

                store = ChatStore()
                try:
                    loaded = store.get_session(session.id)
                    self.assertIsNotNone(loaded)
                    assert loaded is not None
                    self.assertEqual(loaded.tags, ("keep",))
                finally:
                    store.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)


if __name__ == "__main__":
    unittest.main()
