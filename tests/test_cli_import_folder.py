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


class CliImportFolderTests(unittest.TestCase):
    def test_import_folder_json_creates_additive_session_copies(self) -> None:
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
                    source = store.create_session(
                        title="Source Folder",
                        profile="openai",
                        model="gpt-5.5",
                        system_prompt="Source system",
                        folder_id=folder.id,
                    )
                    store.set_session_tags(source.id, ["Folder Tag"])
                    store.add_message(source.id, "user", "Hallo Folder")
                    store.add_message(source.id, "assistant", "Antwort Folder")
                finally:
                    store.close()

                export_path = Path(tmp) / "folder.json"
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["export-folder", "Arbeit", "--json", "-o", str(export_path)]), 0)

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["import-folder", str(export_path), "--folder", "Importiert", "--json"]),
                        0,
                    )
                result = json.loads(out.getvalue())
                self.assertEqual(result["messages"], 2)
                self.assertEqual(result["imported"]["folder"]["name"], "Importiert")
                self.assertEqual(len(result["imported"]["sessions"]), 1)
                imported_id = result["imported"]["sessions"][0]["id"]
                self.assertNotEqual(imported_id, source.id)

                store = ChatStore()
                try:
                    imported = store.get_session(imported_id)
                    self.assertIsNotNone(imported)
                    assert imported is not None
                    self.assertEqual(imported.title, "Source Folder")
                    self.assertEqual(imported.profile, "openai")
                    self.assertEqual(imported.model, "gpt-5.5")
                    self.assertEqual(imported.system_prompt, "Source system")
                    self.assertEqual(imported.tags, ("folder-tag",))
                    self.assertEqual(
                        [(message.role, message.content) for message in store.messages(imported.id)],
                        [("user", "Hallo Folder"), ("assistant", "Antwort Folder")],
                    )
                    folder = store.get_folder(imported.folder_id or "")
                    self.assertIsNotNone(folder)
                    assert folder is not None
                    self.assertEqual(folder.name, "Importiert")
                finally:
                    store.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_import_folder_rejects_invalid_sessions_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["init"]), 0)
                import_path = Path(tmp) / "invalid-folder.json"
                import_path.write_text(
                    json.dumps(
                        {
                            "format": "telachat.folder.v1",
                            "folder": {"kind": "folder", "name": "Bad Folder"},
                            "sessions": [
                                {
                                    "session": {"title": "Good"},
                                    "messages": [{"role": "user", "content": "Noch nicht schreiben"}],
                                },
                                {
                                    "session": {"title": "Bad"},
                                    "messages": [{"role": "tool", "content": "ungueltig"}],
                                },
                            ],
                        }
                    ),
                    encoding="utf-8",
                )

                err = io.StringIO()
                with redirect_stderr(err):
                    self.assertEqual(main(["import-folder", str(import_path)]), 1)
                self.assertIn("Ungueltige Importrolle", err.getvalue())

                store = ChatStore()
                try:
                    self.assertEqual(store.list_sessions(limit=10), [])
                    self.assertEqual(store.list_folders(), [])
                finally:
                    store.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_import_folder_dry_run_validates_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["init"]), 0)
                import_path = Path(tmp) / "folder.json"
                import_path.write_text(
                    json.dumps(
                        {
                            "format": "telachat.folder.v1",
                            "folder": {
                                "kind": "folder",
                                "name": "Dry Folder",
                                "system_prompt": "Dry system",
                            },
                            "sessions": [
                                {
                                    "session": {
                                        "title": "Dry Run",
                                        "profile": "openai",
                                        "model": "gpt-5.5",
                                        "system_prompt": "Dry session",
                                    },
                                    "messages": [
                                        {"role": "user", "content": "Nur pruefen"},
                                        {"role": "assistant", "content": "OK"},
                                    ],
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        main(["import-folder", str(import_path), "--dry-run", "--json"]),
                        0,
                    )
                result = json.loads(out.getvalue())
                self.assertTrue(result["dry_run"])
                self.assertEqual(result["folder"]["name"], "Dry Folder")
                self.assertEqual(result["messages"], 2)
                self.assertEqual(result["sessions"][0]["title"], "Dry Run")
                self.assertEqual(result["sessions"][0]["messages"], 2)

                store = ChatStore()
                try:
                    self.assertEqual(store.list_sessions(limit=10), [])
                    self.assertEqual(store.list_folders(), [])
                finally:
                    store.close()
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)

    def test_import_folder_empty_bundle_recreates_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            try:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["init"]), 0)
                import_path = Path(tmp) / "empty-folder.json"
                import_path.write_text(
                    json.dumps(
                        {
                            "format": "telachat.folder.v1",
                            "folder": {
                                "kind": "folder",
                                "name": "Leer",
                                "system_prompt": "Leerer Kontext",
                            },
                            "sessions": [],
                        }
                    ),
                    encoding="utf-8",
                )

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["import-folder", str(import_path), "--json"]), 0)
                result = json.loads(out.getvalue())
                self.assertEqual(result["messages"], 0)
                self.assertEqual(result["imported"]["sessions"], [])
                self.assertEqual(result["imported"]["folder"]["name"], "Leer")
                self.assertEqual(result["imported"]["folder"]["system_prompt"], "Leerer Kontext")
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)


if __name__ == "__main__":
    unittest.main()
