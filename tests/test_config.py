from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from telachat.config import (
    ConfigError,
    ensure_default_config,
    load_config,
    redact_secret,
    set_config_app_icon,
    set_config_chat_background_image,
    set_config_header_validation,
    set_config_skill_watchdog_enabled,
    set_config_theme,
)


class ConfigTests(unittest.TestCase):
    def test_default_config_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            ensure_default_config(path)
            cfg = load_config(path)
            profile = cfg.profile()
            self.assertEqual(profile.name, "huggingface")
            self.assertEqual(profile.model, "TKI")
            self.assertEqual(profile.api_model, "Qwen/Qwen2.5-1.5B-Instruct")
            self.assertEqual(cfg.profile("tki").name, "huggingface")
            self.assertNotIn("tki", cfg.profiles)
            self.assertIn("TKI", profile.models)
            self.assertIn("Qwen/Qwen2.5-1.5B-Instruct", profile.models)
            self.assertTrue(profile.base_url.endswith("/v1"))
            self.assertIn("huggingface", cfg.profiles)
            self.assertIn("openai", cfg.profiles)
            self.assertIn("lmstudio", cfg.profiles)
            self.assertIn("ollama", cfg.profiles)
            self.assertIn("jan", cfg.profiles)
            self.assertIn("codex", cfg.profiles)
            self.assertNotIn("chatgpt", cfg.profiles)
            self.assertEqual(cfg.profiles["openai"].model, "gpt-5.5")
            self.assertIn("gpt-5.5", cfg.profiles["openai"].models)
            self.assertEqual(cfg.profiles["openai"].reasoning_effort, "high")
            self.assertFalse(cfg.profiles["openai"].send_temperature)
            self.assertFalse(cfg.profiles["openai"].send_top_p)
            self.assertEqual(cfg.profiles["lmstudio"].base_url, "http://localhost:1234/v1")
            self.assertEqual(cfg.profiles["lmstudio"].api_key, "lm-studio")
            self.assertEqual(cfg.profiles["ollama"].base_url, "http://localhost:11434/v1")
            self.assertIn("llama3.2", cfg.profiles["ollama"].models)
            self.assertEqual(cfg.profiles["jan"].api_key, "env:TELACHAT_JAN_API_KEY")
            self.assertEqual(cfg.profiles["codex"].api_mode, "codex")
            self.assertEqual(cfg.theme, "system")
            self.assertEqual(cfg.app_icon, "system")
            self.assertEqual(cfg.chat_background_image, "")
            self.assertTrue(cfg.validate_profile_headers)
            self.assertTrue(cfg.skill_watchdog_enabled)
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

    def test_set_theme_only_updates_top_level_theme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                """
default_profile = "demo"

[profiles.demo]
base_url = "http://127.0.0.1:1/v1"
api_key = ""
model = "demo"
theme = "profile-local"
""".strip(),
                encoding="utf-8",
            )
            self.assertEqual(set_config_theme("dark", path), "dark")
            text = path.read_text(encoding="utf-8")
            self.assertIn('default_profile = "demo"\ntheme = "dark"', text)
            self.assertIn('theme = "profile-local"', text)
            self.assertEqual(load_config(path).theme, "dark")

    def test_header_validation_config_and_setter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            ensure_default_config(path)
            self.assertFalse(set_config_header_validation(False, path))
            cfg = load_config(path)
            self.assertFalse(cfg.validate_profile_headers)
            self.assertIn(
                "validate_profile_headers = false",
                path.read_text(encoding="utf-8"),
            )

            self.assertTrue(set_config_header_validation(True, path))
            self.assertTrue(load_config(path).validate_profile_headers)

    def test_set_header_validation_only_updates_top_level_option(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                """
default_profile = "demo"
theme = "system"
validate_profile_headers = true

[profiles.demo]
base_url = "http://127.0.0.1:1/v1"
api_key = ""
model = "demo"
validate_profile_headers = false
""".strip(),
                encoding="utf-8",
            )
            self.assertFalse(set_config_header_validation(False, path))
            text = path.read_text(encoding="utf-8")
            self.assertIn('theme = "system"\nvalidate_profile_headers = false', text)
            self.assertIn("validate_profile_headers = false", text.split("[profiles.demo]")[1])
            self.assertFalse(load_config(path).validate_profile_headers)

    def test_gui_option_setters_update_top_level_options(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                """
default_profile = "demo"
theme = "system"
validate_profile_headers = true

[profiles.demo]
base_url = "http://127.0.0.1:1/v1"
api_key = ""
model = "demo"
app_icon = "profile-local"
skill_watchdog_enabled = false
""".strip(),
                encoding="utf-8",
            )

            self.assertEqual(set_config_app_icon("random", path), "random")
            self.assertEqual(
                set_config_chat_background_image('/tmp/bg "eins".png', path),
                '/tmp/bg "eins".png',
            )
            self.assertFalse(set_config_skill_watchdog_enabled(False, path))

            text = path.read_text(encoding="utf-8")
            self.assertIn(
                'theme = "system"\napp_icon = "random"\nchat_background_image = "/tmp/bg \\"eins\\".png"',
                text,
            )
            self.assertIn("validate_profile_headers = true\nskill_watchdog_enabled = false", text)
            self.assertIn('app_icon = "profile-local"', text.split("[profiles.demo]")[1])
            cfg = load_config(path)
            self.assertEqual(cfg.app_icon, "random")
            self.assertEqual(cfg.chat_background_image, '/tmp/bg "eins".png')
            self.assertFalse(cfg.skill_watchdog_enabled)

            with self.assertRaises(ValueError):
                set_config_app_icon("nicht-da", path)

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

    def test_profile_model_aliases_and_generation_parameter_flags_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                """
default_profile = "local"

[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "test"
model = "Friendly"
models = ["Friendly", "real-model"]
send_temperature = false
send_top_p = false

[profiles.local.model_aliases]
Friendly = "real-model"
""".strip(),
                encoding="utf-8",
            )
            profile = load_config(path).profile()
            self.assertEqual(profile.api_model, "real-model")
            self.assertFalse(profile.send_temperature)
            self.assertFalse(profile.send_top_p)

    def test_profile_alias_does_not_shadow_existing_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                """
default_profile = "tki"

[profiles.tki]
base_url = "http://127.0.0.1:1/v1"
api_key = "test"
model = "legacy-model"
""".strip(),
                encoding="utf-8",
            )
            cfg = load_config(path)

            self.assertEqual(cfg.profile().name, "tki")
            self.assertEqual(cfg.profile("tki").name, "tki")
            self.assertEqual(cfg.profile().model, "legacy-model")

    def test_profile_stream_and_api_mode_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                """
default_profile = "local"
[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "test"
model = "demo"
stream = "false"
""".strip(),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ConfigError, "stream"):
                load_config(path)

            path.write_text(
                """
default_profile = "local"
[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "test"
model = "demo"
api_mode = "unknown_mode"
""".strip(),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ConfigError, "api_mode"):
                load_config(path)

    def test_profile_headers_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            profile_base = """
default_profile = "local"
[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "test"
model = "demo"
"""
            path.write_text(
                profile_base
                + """
[profiles.local.headers]
HTTP-Referer = "https://local.telachat"
X-Title = "Telachat"
""",
                encoding="utf-8",
            )
            self.assertEqual(
                load_config(path).profile().extra_headers,
                {
                    "HTTP-Referer": "https://local.telachat",
                    "X-Title": "Telachat",
                },
            )

            cases = [
                ('headers = "bad"\n', "headers"),
                ('[profiles.local.headers]\n"Bad Header" = "x"\n', "Header-Namen"),
                ('[profiles.local.headers]\n"Bad:Header" = "x"\n', "Header-Namen"),
                ('[profiles.local.headers]\nX-Test = "line\\nbreak"\n', "Header-Wert"),
                ("[profiles.local.headers]\nX-Test = 7\n", "headers"),
            ]
            for suffix, pattern in cases:
                with self.subTest(suffix=suffix):
                    path.write_text(profile_base + suffix, encoding="utf-8")
                    with self.assertRaisesRegex(ConfigError, pattern):
                        load_config(path)

            path.write_text(
                """
default_profile = "local"
validate_profile_headers = false
[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "test"
model = "demo"

[profiles.local.headers]
"Bad@Header" = "ok"
""".strip(),
                encoding="utf-8",
            )
            self.assertEqual(
                load_config(path).profile().extra_headers,
                {"Bad@Header": "ok"},
            )

            disabled_validation_cases = [
                ('[profiles.local.headers]\n"Bad Header" = "x"\n', "Header-Namen"),
                ('[profiles.local.headers]\n"Bad:Header" = "x"\n', "Header-Namen"),
                ('[profiles.local.headers]\n"Bad\\u00dcHeader" = "x"\n', "Header-Namen"),
                ('[profiles.local.headers]\nX-Test = "line\\nbreak"\n', "Header-Wert"),
            ]
            for suffix, pattern in disabled_validation_cases:
                with self.subTest(disabled_validation_suffix=suffix):
                    path.write_text(
                        """
default_profile = "local"
validate_profile_headers = false
[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "test"
model = "demo"

""".lstrip()
                        + suffix,
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(ConfigError, pattern):
                        load_config(path)

            path.write_text(
                """
default_profile = "local"
validate_profile_headers = false
[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "test"
model = "demo"
headers = "bad"
""".strip(),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ConfigError, "headers"):
                load_config(path)

    def test_numeric_config_values_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            profile_base = """
default_profile = "local"
[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "test"
model = "demo"
"""
            cases = [
                ("temperature = true", "temperature"),
                ("temperature = -0.1", "temperature"),
                ("temperature = 2.1", "temperature"),
                ('top_p = "nope"', "top_p"),
                ("top_p = -0.1", "top_p"),
                ("top_p = 1.1", "top_p"),
                ("max_tokens = 0", "max_tokens"),
                ('timeout_seconds = "slow"', "timeout_seconds"),
            ]
            for line, pattern in cases:
                with self.subTest(line=line):
                    path.write_text(profile_base + line + "\n", encoding="utf-8")
                    with self.assertRaisesRegex(ConfigError, pattern):
                        load_config(path)

            path.write_text(
                """
default_profile = "local"
max_history_messages = 0
[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "test"
model = "demo"
""".strip(),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ConfigError, "max_history_messages"):
                load_config(path)

            path.write_text(profile_base, encoding="utf-8")
            cfg = load_config(path)
            with self.assertRaisesRegex(ConfigError, "max_tokens"):
                cfg.profile().with_overrides(max_tokens=0)
            with self.assertRaisesRegex(ConfigError, "temperature"):
                cfg.profile().with_overrides(temperature=2.1)

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

    def test_secret_sources_preserve_windows_backslashes_in_basic_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "new" / "test.env"
            file_path = Path(tmp) / "new" / "file-secret.txt"
            env_path.parent.mkdir(parents=True, exist_ok=True)
            env_path.write_text(
                "OPENAI_API_KEY=windows-envfile-secret\n",
                encoding="utf-8",
            )
            file_path.write_text("windows-file-secret\n", encoding="utf-8")
            path = Path(tmp) / "config.toml"
            path.write_text(
                f"""
default_profile = "envfile"

[profiles.envfile]
base_url = "https://api.openai.com/v1"
api_key = "envfile:{env_path}#OPENAI_API_KEY"
model = "demo"

[profiles.file]
base_url = "https://api.openai.com/v1"
api_key = "file:{file_path}"
model = "demo"
""".strip(),
                encoding="utf-8",
            )
            cfg = load_config(path)
            self.assertEqual(cfg.profile("envfile").resolved_api_key(), "windows-envfile-secret")
            self.assertEqual(cfg.profile("file").resolved_api_key(), "windows-file-secret")

    def test_secret_sources_preserve_raw_unc_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                r"""
default_profile = "unc"

[profiles.unc]
base_url = "https://api.openai.com/v1"
api_key = "envfile:\\server\share\secret.env#OPENAI_API_KEY"
model = "demo"
""".strip(),
                encoding="utf-8",
            )
            cfg = load_config(path)
            self.assertEqual(
                cfg.profile().api_key,
                r"envfile:\\server\share\secret.env#OPENAI_API_KEY",
            )

    def test_missing_secret_files_raise_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            missing_secret = Path(tmp) / "missing.secret"
            config_path.write_text(
                f"""
default_profile = "local"
[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "file:{missing_secret}"
model = "demo"
""".strip(),
                encoding="utf-8",
            )
            cfg = load_config(config_path)
            with self.assertRaisesRegex(ConfigError, "Secret-Datei kann nicht gelesen"):
                cfg.profile().resolved_api_key()

            missing_envfile = Path(tmp) / "missing.env"
            config_path.write_text(
                f"""
default_profile = "local"
[profiles.local]
base_url = "http://127.0.0.1:1/v1"
api_key = "envfile:{missing_envfile}#OPENAI_API_KEY"
model = "demo"
""".strip(),
                encoding="utf-8",
            )
            cfg = load_config(config_path)
            with self.assertRaisesRegex(ConfigError, "envfile kann nicht gelesen"):
                cfg.profile().resolved_api_key()

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
