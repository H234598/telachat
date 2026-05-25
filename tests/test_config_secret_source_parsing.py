from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from telachat.config import load_config


class ConfigSecretSourceParsingTests(unittest.TestCase):
    def test_basic_string_secret_sources_keep_escape_like_backslashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(
                r"""
default_profile = "envfile"

[profiles.envfile]
base_url = "http://127.0.0.1:1/v1"
api_key = "envfile:C:\new\tab.env#OPENAI_API_KEY"
model = "demo"

[profiles.file]
base_url = "http://127.0.0.1:1/v1"
api_key = "file:C:\tab\new-token.txt"
model = "demo"
""".strip(),
                encoding="utf-8",
            )

            cfg = load_config(config_path)

            self.assertEqual(
                cfg.profile("envfile").api_key,
                r"envfile:C:\new\tab.env#OPENAI_API_KEY",
            )
            self.assertEqual(
                cfg.profile("file").api_key,
                r"file:C:\tab\new-token.txt",
            )


if __name__ == "__main__":
    unittest.main()
