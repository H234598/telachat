from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from telachat.cli import main
from telachat.store import ChatStore


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


class CliExportFolderJsonTests(unittest.TestCase):
    def test_export_folder_json_covers_all_and_unfiled_virtual_folders(self) -> None:
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
                    work = store.create_folder("Arbeit")
                    filed = store.create_session(
                        title="Filed",
                        profile="openai",
                        model="gpt-5.5",
                        system_prompt="Filed system",
                        folder_id=work.id,
                    )
                    unfiled = store.create_session(
                        title="Unfiled",
                        profile="tki",
                        model="Qwen/Qwen2.5-1.5B-Instruct",
                        system_prompt="Unfiled system",
                    )
                    store.add_message(filed.id, "user", "Filed message")
                    store.add_message(unfiled.id, "user", "Unfiled message")
                finally:
                    store.close()

                all_out = io.StringIO()
                with redirect_stdout(all_out):
                    self.assertEqual(main(["export-folder", "all", "--json"]), 0)
                all_payload = json.loads(all_out.getvalue())
                self.assertEqual(all_payload["folder"]["kind"], "all")
                self.assertEqual(all_payload["folder"]["name"], "Alle Sessions")
                self.assertEqual(
                    {item["session"]["title"] for item in all_payload["sessions"]},
                    {"Filed", "Unfiled"},
                )

                unfiled_out = io.StringIO()
                with redirect_stdout(unfiled_out):
                    self.assertEqual(main(["export-folder", "none", "--json"]), 0)
                unfiled_payload = json.loads(unfiled_out.getvalue())
                self.assertEqual(unfiled_payload["folder"]["kind"], "unfiled")
                self.assertEqual(unfiled_payload["folder"]["name"], "Ohne Ordner")
                self.assertEqual(
                    [item["session"]["title"] for item in unfiled_payload["sessions"]],
                    ["Unfiled"],
                )
                encoded = json.dumps(unfiled_payload, sort_keys=True)
                self.assertIn("Unfiled message", encoded)
                self.assertNotIn("Filed message", encoded)
                self.assertNotIn("api_key", encoded)
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)


if __name__ == "__main__":
    unittest.main()
