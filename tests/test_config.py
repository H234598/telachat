from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from telachat.config import ensure_default_config, load_config, redact_secret, set_config_theme


class ConfigTests(unittest.TestCase):
    def test_default_config_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            ensure_default_config(path)
            cfg = load_config(path)
            profile = cfg.profile()
            self.assertEqual(profile.name, "tki")
            self.assertEqual(profile.model, "Qwen/Qwen2.5-1.5B-Instruct")
            self.assertIn("Qwen/Qwen2.5-1.5B-Instruct", profile.models)
            self.assertTrue(profile.base_url.endswith("/v1"))
            self.assertIn("huggingface", cfg.profiles)
            self.assertIn("openai", cfg.profiles)
            self.assertIn("codex", cfg.profiles)
            self.assertNotIn("chatgpt", cfg.profiles)
            self.assertEqual(cfg.profiles["openai"].model, "gpt-5.5")
            self.assertIn("gpt-5.5", cfg.profiles["openai"].models)
            self.assertEqual(cfg.profiles["openai"].reasoning_effort, "high")
            self.assertEqual(cfg.profiles["codex"].api_mode, "codex")
            self.assertEqual(cfg.theme, "system")
            self.assertIn("summarize", cfg.prompt_templates)
            self.assertIn("{input}", cfg.prompt_templates["summarize"])

    def test_theme_config_and_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            ensure_default_config(path)
            self.assertEqual(set_config_theme("dark", path), "dark")
            cfg = load_config(path)
            self.assertEqual(cfg.theme, "dark")
            self.assertIn('theme = "dark"', path.read_text(encoding="utf-8"))

            old_theme = os.environ.get("TELACHAT_THEME")
            os.environ["TELACHAT_THEME"] = "highcontrast"
            try:
                cfg = load_config(path)
                self.assertEqual(cfg.theme, "high-contrast")
            finally:
                _restore_env("TELACHAT_THEME", old_theme)

            with self.assertRaises(ValueError):
                set_config_theme("neon-glitter", path)

    def test_custom_prompt_templates_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                """
default_profile = "local"
[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "test"
model = "demo"

[prompt_templates]
ticket = "Schreibe ein Ticket:\\n\\n{input}"
""".strip(),
                encoding="utf-8",
            )
            cfg = load_config(path)
            self.assertEqual(cfg.prompt_templates, {"ticket": "Schreibe ein Ticket:\n\n{input}"})

    def test_env_api_key_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                """
default_profile = "local"
[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "env:TELACHAT_TEST_KEY"
model = "demo"
""".strip(),
                encoding="utf-8",
            )
            os.environ["TELACHAT_TEST_KEY"] = "secret-value"
            try:
                cfg = load_config(path)
                self.assertEqual(cfg.profile().resolved_api_key(), "secret-value")
            finally:
                os.environ.pop("TELACHAT_TEST_KEY", None)

    def test_envfile_api_key_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "openai.env"
            env_path.write_text(
                "OTHER=nope\nOPENAI_API_KEY='envfile-secret'\n",
                encoding="utf-8",
            )
            path = Path(tmp) / "config.toml"
            path.write_text(
                f"""
default_profile = "openai"
[profiles.openai]
base_url = "https://api.openai.com/v1"
api_key = "envfile:{env_path}#OPENAI_API_KEY"
model = "demo"
""".strip(),
                encoding="utf-8",
            )
            cfg = load_config(path)
            self.assertEqual(cfg.profile().resolved_api_key(), "envfile-secret")

    def test_redact_secret(self) -> None:
        self.assertEqual(redact_secret("hf-space"), "<redacted>")
        self.assertEqual(redact_secret("env:KEY"), "env:KEY")
        self.assertEqual(redact_secret("envfile:/x#KEY"), "envfile:/x#KEY")
        self.assertEqual(redact_secret("sk-1234567890"), "sk-...890")


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
