from __future__ import annotations

import os
import re
import stat
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .defaults import (
    DEFAULT_CONFIG,
    DEFAULT_PROFILE,
    DEFAULT_PROMPT_TEMPLATES,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_THEME,
)
from .paths import config_path
from .themes import normalize_theme_name, theme_choices


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Profile:
    name: str
    label: str
    base_url: str
    api_key: str
    model: str
    models: list[str] | None = None
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 512
    reasoning_effort: str | None = None
    timeout_seconds: int = 300
    stream: bool = True
    api_mode: str = "chat_completions"
    extra_headers: dict[str, str] | None = None

    @property
    def display_name(self) -> str:
        return self.label or self.name

    def resolved_api_key(self) -> str:
        key = self.api_key or ""
        if key.startswith("env:"):
            env_name = key[4:].strip()
            return os.environ.get(env_name, "")
        if key.startswith("envfile:"):
            return _read_envfile_secret(key[8:].strip())
        if key.startswith("file:"):
            file_name = key[5:].strip()
            try:
                return Path(file_name).expanduser().read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise ConfigError(f"Secret-Datei kann nicht gelesen werden: {file_name}") from exc
        return key

    def with_overrides(
        self,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
        stream: bool | None = None,
    ) -> "Profile":
        updates: dict[str, Any] = {}
        if model is not None:
            updates["model"] = model
        if temperature is not None:
            updates["temperature"] = temperature
        if max_tokens is not None:
            updates["max_tokens"] = max_tokens
        if reasoning_effort is not None:
            updates["reasoning_effort"] = reasoning_effort
        if stream is not None:
            updates["stream"] = stream
        return replace(self, **updates)


@dataclass(frozen=True)
class AppConfig:
    path: Path
    default_profile: str
    theme: str
    default_system_prompt: str
    max_history_messages: int
    profiles: dict[str, Profile]
    prompt_templates: dict[str, str]

    def profile(self, name: str | None = None) -> Profile:
        wanted = name or self.default_profile
        try:
            return self.profiles[wanted]
        except KeyError as exc:
            available = ", ".join(sorted(self.profiles)) or "<none>"
            raise ConfigError(
                f"Profil '{wanted}' existiert nicht. Verfuegbar: {available}"
            ) from exc


def ensure_default_config(path: Path | None = None, *, force: bool = False) -> Path:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        return target
    target.write_text(DEFAULT_CONFIG, encoding="utf-8")
    try:
        target.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except PermissionError:
        pass
    return target


def load_config(path: Path | None = None, *, create: bool = True) -> AppConfig:
    target = path or config_path()
    if create:
        ensure_default_config(target)
    if not target.exists():
        raise ConfigError(f"Konfigurationsdatei fehlt: {target}")
    raw_text = _escape_secret_source_backslashes(target.read_text(encoding="utf-8"))
    try:
        raw = tomllib.loads(raw_text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Ungueltige TOML-Konfiguration in {target}: {exc}") from exc

    profile_blocks = raw.get("profiles")
    if not isinstance(profile_blocks, dict) or not profile_blocks:
        raise ConfigError("Konfiguration braucht mindestens einen [profiles.NAME]-Block.")

    profiles: dict[str, Profile] = {}
    for name, values in profile_blocks.items():
        if not isinstance(values, dict):
            raise ConfigError(f"Profil '{name}' ist kein TOML-Objekt.")
        base_url = _required_string(values, "base_url", name).rstrip("/")
        api_key = str(values.get("api_key", ""))
        model = _required_string(values, "model", name)
        headers = values.get("headers")
        if headers is not None:
            if not isinstance(headers, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in headers.items()
            ):
                raise ConfigError(f"Profil '{name}' hat ungueltige headers.")
            extra_headers = dict(headers)
        else:
            extra_headers = None
        profiles[name] = Profile(
            name=name,
            label=str(values.get("label", name)),
            base_url=base_url,
            api_key=api_key,
            model=model,
            models=_models(values, model, name),
            temperature=float(values.get("temperature", 0.2)),
            top_p=float(values.get("top_p", 0.9)),
            max_tokens=int(values.get("max_tokens", 512)),
            reasoning_effort=_optional_reasoning_effort(values.get("reasoning_effort"), name),
            timeout_seconds=int(values.get("timeout_seconds", 300)),
            stream=_bool(values, "stream", True, name),
            api_mode=_api_mode(values.get("api_mode", "chat_completions"), name),
            extra_headers=extra_headers,
        )

    default_profile = str(raw.get("default_profile", DEFAULT_PROFILE))
    if default_profile not in profiles:
        default_profile = next(iter(profiles))
    theme = _theme(raw.get("theme", DEFAULT_THEME))
    return AppConfig(
        path=target,
        default_profile=default_profile,
        theme=theme,
        default_system_prompt=str(raw.get("default_system_prompt", DEFAULT_SYSTEM_PROMPT)),
        max_history_messages=int(raw.get("max_history_messages", 24)),
        profiles=profiles,
        prompt_templates=_prompt_templates(raw.get("prompt_templates", DEFAULT_PROMPT_TEMPLATES)),
    )


def set_config_theme(value: str, path: Path | None = None) -> str:
    theme = normalize_theme_name(value)
    target = ensure_default_config(path)
    text = target.read_text(encoding="utf-8")
    replacement = f'theme = "{theme}"'
    lines = text.splitlines()
    default_profile_index: int | None = None
    first_table_index = len(lines)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("["):
            first_table_index = index
            break
        before, sep, _after = line.partition("=")
        if not sep:
            continue
        key = before.strip()
        if key == "theme":
            lines[index] = replacement
            target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            return theme
        if key == "default_profile":
            default_profile_index = index
    insert_index = (
        default_profile_index + 1 if default_profile_index is not None else first_table_index
    )
    lines.insert(insert_index, replacement)
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return theme


def redact_secret(value: str) -> str:
    if not value:
        return "<empty>"
    if value.startswith(("env:", "envfile:", "file:")):
        return value
    if len(value) <= 8:
        return "<redacted>"
    return f"{value[:3]}...{value[-3:]}"


def _required_string(values: dict[str, Any], key: str, profile_name: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Profil '{profile_name}' braucht '{key}'.")
    return value.strip()


def _models(values: dict[str, Any], default_model: str, profile_name: str) -> list[str]:
    raw = values.get("models")
    if raw is None:
        return [default_model]
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigError(f"Profil '{profile_name}' hat ungueltige models-Liste.")
    clean = [item.strip() for item in raw if item.strip()]
    if default_model not in clean:
        clean.insert(0, default_model)
    return clean


def _optional_reasoning_effort(value: object, profile_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigError(f"Profil '{profile_name}' hat ungueltiges reasoning_effort.")
    clean = value.strip().lower()
    if not clean:
        return None
    allowed = {"none", "minimal", "low", "medium", "high", "xhigh"}
    if clean not in allowed:
        raise ConfigError(
            f"Profil '{profile_name}' hat ungueltiges reasoning_effort: {value}"
        )
    return clean


def _bool(values: dict[str, Any], key: str, default: bool, profile_name: str) -> bool:
    value = values.get(key, default)
    if isinstance(value, bool):
        return value
    raise ConfigError(f"Profil '{profile_name}' hat ungueltiges {key}.")


def _api_mode(value: object, profile_name: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"Profil '{profile_name}' hat ungueltiges api_mode.")
    clean = value.strip().lower()
    allowed = {"chat_completions", "responses", "codex"}
    if clean not in allowed:
        raise ConfigError(f"Profil '{profile_name}' hat ungueltiges api_mode: {value}")
    return clean


def _theme(value: object) -> str:
    override = os.environ.get("TELACHAT_THEME")
    try:
        return normalize_theme_name(override if override is not None else value)
    except ValueError as exc:
        available = ", ".join(theme_choices())
        raise ConfigError(f"{exc}. Erlaubt: {available}") from exc


def _prompt_templates(raw: object) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError("[prompt_templates] muss ein TOML-Objekt sein.")
    templates: dict[str, str] = {}
    for name, value in raw.items():
        clean_name = str(name).strip()
        if not clean_name:
            raise ConfigError("Prompt-Template mit leerem Namen.")
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"Prompt-Template '{clean_name}' braucht Text.")
        templates[clean_name] = value.strip()
    return dict(sorted(templates.items()))


def _escape_secret_source_backslashes(text: str) -> str:
    return re.sub(
        r'(=\s*")((?:envfile|file):[^"\n]*\\[^"\n]*)(")',
        lambda match: match.group(1)
        + _escape_lone_backslashes(match.group(2))
        + match.group(3),
        text,
    )


def _escape_lone_backslashes(value: str) -> str:
    escaped: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\":
            escaped.append(char)
            index += 1
            continue
        escaped.append("\\\\")
        if index + 1 < len(value) and value[index + 1] == "\\":
            index += 2
        else:
            index += 1
    return "".join(escaped)


def _read_envfile_secret(spec: str) -> str:
    if "#" in spec:
        file_name, env_name = spec.rsplit("#", 1)
    elif ":" in spec:
        file_name, env_name = spec.rsplit(":", 1)
    else:
        raise ConfigError("envfile braucht Format envfile:/pfad#VARIABLE.")
    file_path = Path(file_name).expanduser()
    wanted = env_name.strip()
    if not wanted:
        raise ConfigError("envfile braucht einen Variablennamen.")
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ConfigError(f"envfile kann nicht gelesen werden: {file_path}") from exc
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip().removeprefix("export ").strip() == wanted:
            return value.strip().strip("\"'")
    return ""
