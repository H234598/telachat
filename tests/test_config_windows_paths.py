from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from telachat.config import load_config


class ConfigWindowsPathTests(unittest.TestCase):
    def test_secret_source_basic_strings_keep_escape_like_backslashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "new" / "tab.env"
            file_path = Path(tmp) / "tab" / "new-token.txt"
            env_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            env_path.write_text("OPENAI_API_KEY=windows-env-secret\n", encoding="utf-8")
            file_path.write_text("windows-file-secret\n", encoding="utf-8")

            for source, expected in (
                (f"envfile:{env_path}#OPENAI_API_KEY", "windows-env-secret"),
                (f"file:{file_path}", "windows-file-secret"),
            ):
                with self.subTest(source=source):
                    config_path = Path(tmp) / "config.toml"
                    config_path.write_text(
                        f"""
default_profile = "local"
[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "{source}"
model = "demo"
""".strip(),
                        encoding="utf-8",
                    )

                    self.assertEqual(load_config(config_path).profile().resolved_api_key(), expected)


if __name__ == "__main__":
    unittest.main()
