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


class CliExportJsonTests(unittest.TestCase):
    def test_json_export_excludes_provider_configuration_and_raw_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_config = os.environ.get("XDG_CONFIG_HOME")
            old_data = os.environ.get("XDG_DATA_HOME")
            old_openai_key = os.environ.get("OPENAI_API_KEY")
            os.environ["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            os.environ["OPENAI_API_KEY"] = "secret-value"
            try:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["init"]), 0)

                store = ChatStore()
                try:
                    session = store.create_session(
                        title="JSON Contract",
                        profile="openai",
                        model="gpt-5.5",
                        system_prompt="System contract",
                    )
                    store.add_message(session.id, "user", "Hallo Contract")
                finally:
                    store.close()

                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main(["export", session.id, "--json"]), 0)

                payload = json.loads(out.getvalue())
                self.assertEqual(set(payload), {"format", "messages", "session"})
                self.assertEqual(
                    set(payload["session"]),
                    {
                        "created_at",
                        "folder_id",
                        "id",
                        "model",
                        "pinned",
                        "profile",
                        "system_prompt",
                        "tags",
                        "title",
                        "updated_at",
                    },
                )
                self.assertEqual(payload["session"]["tags"], [])
                self.assertEqual(
                    set(payload["messages"][0]),
                    {"content", "created_at", "id", "role", "session_id"},
                )
                encoded = json.dumps(payload, sort_keys=True)
                self.assertNotIn("api_key", encoded)
                self.assertNotIn("secret-value", encoded)
            finally:
                _restore_env("XDG_CONFIG_HOME", old_config)
                _restore_env("XDG_DATA_HOME", old_data)
                _restore_env("OPENAI_API_KEY", old_openai_key)


if __name__ == "__main__":
    unittest.main()
