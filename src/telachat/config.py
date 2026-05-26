from __future__ import annotations

import json
import math
import os
import re
import stat
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .assets import normalize_icon_name
from .defaults import (
    DEFAULT_CONFIG,
    DEFAULT_APP_ICON,
    DEFAULT_CHAT_BACKGROUND_IMAGE,
    DEFAULT_PROFILE,
    DEFAULT_PROMPT_TEMPLATES,
    DEFAULT_SKILL_WATCHDOG_ENABLED,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_THEME,
)
from .paths import config_path
from .themes import normalize_theme_name, theme_choices


class ConfigError(RuntimeError):
    pass


_HEADER_NAME_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_HEADER_NAME_SAFETY_RE = re.compile(r"^[!-9;-~]+$")
_PROFILE_ALIASES = {"tki": "huggingface"}


@dataclass(frozen=True)
class Profile:
    name: str
    label: str
    base_url: str
    api_key: str
    model: str
    models: list[str] | None = None
    model_aliases: dict[str, str] | None = None
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 512
    reasoning_effort: str | None = None
    timeout_seconds: int = 300
    stream: bool = True
    api_mode: str = "chat_completions"
    send_temperature: bool = True
    send_top_p: bool = True
    extra_headers: dict[str, str] | None = None

    @property
    def display_name(self) -> str:
        return self.label or self.name

    @property
    def api_model(self) -> str:
        aliases = self.model_aliases or {}
        return aliases.get(self.model, self.model)

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
            updates["temperature"] = _number_between(
                temperature,
                "temperature",
                self.name,
                minimum=0.0,
                maximum=2.0,
            )
        if max_tokens is not None:
            updates["max_tokens"] = _positive_int(max_tokens, "max_tokens", self.name)
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
    app_icon: str
    chat_background_image: str
    validate_profile_headers: bool
    skill_watchdog_enabled: bool
    default_system_prompt: str
    max_history_messages: int
    profiles: dict[str, Profile]
    prompt_templates: dict[str, str]

    def profile(self, name: str | None = None) -> Profile:
        wanted = name or self.default_profile
        if wanted not in self.profiles:
            wanted = _PROFILE_ALIASES.get(wanted, wanted)
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

    validate_profile_headers = _global_bool(raw, "validate_profile_headers", True)
    skill_watchdog_enabled = _global_bool(
        raw,
        "skill_watchdog_enabled",
        DEFAULT_SKILL_WATCHDOG_ENABLED,
    )
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
        extra_headers = _headers(
            values.get("headers"),
            name,
            validate=validate_profile_headers,
        )
        profiles[name] = Profile(
            name=name,
            label=str(values.get("label", name)),
            base_url=base_url,
            api_key=api_key,
            model=model,
            models=_models(values, model, name),
            model_aliases=_string_map(values.get("model_aliases"), name, "model_aliases"),
            temperature=_number_between(
                values.get("temperature", 0.2),
                "temperature",
                name,
                minimum=0.0,
                maximum=2.0,
            ),
            top_p=_number_between(
                values.get("top_p", 0.9),
                "top_p",
                name,
                minimum=0.0,
                maximum=1.0,
            ),
            max_tokens=_positive_int(values.get("max_tokens", 512), "max_tokens", name),
            reasoning_effort=_optional_reasoning_effort(values.get("reasoning_effort"), name),
            timeout_seconds=_positive_int(
                values.get("timeout_seconds", 300), "timeout_seconds", name
            ),
            stream=_bool(values, "stream", True, name),
            api_mode=_api_mode(values.get("api_mode", "chat_completions"), name),
            send_temperature=_bool(values, "send_temperature", True, name),
            send_top_p=_bool(values, "send_top_p", True, name),
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
        app_icon=_app_icon(raw.get("app_icon", DEFAULT_APP_ICON)),
        chat_background_image=_optional_string(
            raw.get("chat_background_image", DEFAULT_CHAT_BACKGROUND_IMAGE),
            "chat_background_image",
        ),
        validate_profile_headers=validate_profile_headers,
        skill_watchdog_enabled=skill_watchdog_enabled,
        default_system_prompt=str(raw.get("default_system_prompt", DEFAULT_SYSTEM_PROMPT)),
        max_history_messages=_positive_int(
            raw.get("max_history_messages", 24), "max_history_messages", None
        ),
        profiles=profiles,
        prompt_templates=_prompt_templates(raw.get("prompt_templates", DEFAULT_PROMPT_TEMPLATES)),
    )


def set_config_theme(value: str, path: Path | None = None) -> str:
    theme = normalize_theme_name(value)
    target = ensure_default_config(path)
    replacement = f'theme = "{theme}"'
    _set_top_level_assignment(target, "theme", replacement, after_key="default_profile")
    return theme


def set_config_app_icon(value: str, path: Path | None = None) -> str:
    icon = normalize_icon_name(value)
    target = ensure_default_config(path)
    replacement = f'app_icon = "{icon}"'
    _set_top_level_assignment(target, "app_icon", replacement, after_key="theme")
    return icon


def set_config_chat_background_image(value: str, path: Path | None = None) -> str:
    background = str(value or "").strip()
    target = ensure_default_config(path)
    replacement = f'chat_background_image = "{_toml_basic_string(background)}"'
    _set_top_level_assignment(
        target,
        "chat_background_image",
        replacement,
        after_key="app_icon",
    )
    return background


def set_config_header_validation(enabled: bool, path: Path | None = None) -> bool:
    target = ensure_default_config(path)
    replacement = f"validate_profile_headers = {str(bool(enabled)).lower()}"
    _set_top_level_assignment(
        target,
        "validate_profile_headers",
        replacement,
        after_key="theme",
    )
    return bool(enabled)


def set_config_skill_watchdog_enabled(enabled: bool, path: Path | None = None) -> bool:
    target = ensure_default_config(path)
    replacement = f"skill_watchdog_enabled = {str(bool(enabled)).lower()}"
    _set_top_level_assignment(
        target,
        "skill_watchdog_enabled",
        replacement,
        after_key="validate_profile_headers",
    )
    return bool(enabled)


def set_config_prompt_template(name: str, template: str, path: Path | None = None) -> str:
    clean_name, clean_template = _clean_prompt_template(name, template)
    target = ensure_default_config(path)
    templates = dict(load_config(target).prompt_templates)
    templates[clean_name] = clean_template
    _write_prompt_templates(target, templates)
    return clean_template


def rename_config_prompt_template(old_name: str, new_name: str, path: Path | None = None) -> str:
    old_clean = _clean_prompt_template_name(old_name)
    new_clean = _clean_prompt_template_name(new_name)
    target = ensure_default_config(path)
    templates = dict(load_config(target).prompt_templates)
    if old_clean not in templates:
        raise ConfigError(f"Prompt-Template '{old_clean}' fehlt.")
    if new_clean != old_clean and new_clean in templates:
        raise ConfigError(f"Prompt-Template '{new_clean}' existiert bereits.")
    templates[new_clean] = templates.pop(old_clean)
    _write_prompt_templates(target, templates)
    return new_clean


def delete_config_prompt_template(name: str, path: Path | None = None) -> str:
    clean_name = _clean_prompt_template_name(name)
    target = ensure_default_config(path)
    templates = dict(load_config(target).prompt_templates)
    if clean_name not in templates:
        raise ConfigError(f"Prompt-Template '{clean_name}' fehlt.")
    del templates[clean_name]
    _write_prompt_templates(target, templates)
    return clean_name


def _set_top_level_assignment(
    target: Path,
    key: str,
    replacement: str,
    *,
    after_key: str | None = None,
) -> None:
    text = target.read_text(encoding="utf-8")
    lines = text.splitlines()
    after_index: int | None = None
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
        current_key = before.strip()
        if current_key == key:
            lines[index] = replacement
            target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            return
        if after_key is not None and current_key == after_key:
            after_index = index
    insert_index = after_index + 1 if after_index is not None else first_table_index
    lines.insert(insert_index, replacement)
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_prompt_templates(target: Path, templates: dict[str, str]) -> None:
    text = target.read_text(encoding="utf-8")
    lines = text.splitlines()
    start, end = _table_bounds(lines, "prompt_templates")
    block = _prompt_template_block(templates)
    if start is not None:
        replacement = block if block else []
        lines[start:end] = replacement
    elif block:
        insert_index = _first_table_index(lines)
        prefix = [""] if insert_index > 0 and lines[insert_index - 1].strip() else []
        suffix = [""] if insert_index < len(lines) and lines[insert_index].strip() else []
        lines[insert_index:insert_index] = prefix + block + suffix
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _table_bounds(lines: list[str], table: str) -> tuple[int | None, int]:
    header = f"[{table}]"
    start: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == header:
            start = index
            break
    if start is None:
        return None, len(lines)
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].strip().startswith("["):
            end = index
            break
    return start, end


def _first_table_index(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if line.strip().startswith("["):
            return index
    return len(lines)


def _prompt_template_block(templates: dict[str, str]) -> list[str]:
    if not templates:
        return []
    lines = [
        "[prompt_templates]",
        "# Supported variables: {input}, {date}, {time}, {datetime}.",
    ]
    for name, template in sorted(templates.items()):
        lines.append(f"{_toml_key(name)} = {_toml_string(template)}")
    return lines


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


def _string_map(
    raw: object,
    profile_name: str,
    key: str,
) -> dict[str, str] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ConfigError(f"Profil '{profile_name}' hat ungueltiges {key}.")
    result: dict[str, str] = {}
    for name, value in raw.items():
        clean_name = str(name).strip()
        if not clean_name or not isinstance(value, str) or not value.strip():
            raise ConfigError(f"Profil '{profile_name}' hat ungueltiges {key}.")
        result[clean_name] = value.strip()
    return result


def _headers(raw: object, profile_name: str, *, validate: bool) -> dict[str, str] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ConfigError(f"Profil '{profile_name}' hat ungueltige headers.")
    headers: dict[str, str] = {}
    for name, value in raw.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise ConfigError(f"Profil '{profile_name}' hat ungueltige headers.")
        if not _HEADER_NAME_SAFETY_RE.fullmatch(name):
            raise ConfigError(f"Profil '{profile_name}' hat ungueltigen Header-Namen.")
        if validate and not _HEADER_NAME_RE.fullmatch(name):
            raise ConfigError(f"Profil '{profile_name}' hat ungueltigen Header-Namen.")
        if _has_header_control(value):
            raise ConfigError(f"Profil '{profile_name}' hat ungueltigen Header-Wert.")
        headers[name] = value
    return headers


def _has_header_control(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


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


def _number(value: object, key: str, profile_name: str | None) -> float:
    if isinstance(value, bool):
        raise ConfigError(_invalid_config_value(key, profile_name))
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(_invalid_config_value(key, profile_name)) from exc
    if not math.isfinite(result):
        raise ConfigError(_invalid_config_value(key, profile_name))
    return result


def _number_between(
    value: object,
    key: str,
    profile_name: str | None,
    *,
    minimum: float,
    maximum: float,
) -> float:
    result = _number(value, key, profile_name)
    if not minimum <= result <= maximum:
        raise ConfigError(
            f"{_field_label(key, profile_name)} muss zwischen {minimum:g} und {maximum:g} liegen."
        )
    return result


def _positive_int(value: object, key: str, profile_name: str | None) -> int:
    if isinstance(value, bool):
        raise ConfigError(_invalid_config_value(key, profile_name))
    if isinstance(value, int):
        result = value
    elif isinstance(value, str):
        try:
            result = int(value.strip())
        except ValueError as exc:
            raise ConfigError(_invalid_config_value(key, profile_name)) from exc
    else:
        raise ConfigError(_invalid_config_value(key, profile_name))
    if result <= 0:
        raise ConfigError(f"{_field_label(key, profile_name)} muss groesser als 0 sein.")
    return result


def _invalid_config_value(key: str, profile_name: str | None) -> str:
    return f"{_field_label(key, profile_name)} ist ungueltig."


def _field_label(key: str, profile_name: str | None) -> str:
    if profile_name is None:
        return f"Konfiguration {key}"
    return f"Profil '{profile_name}' {key}"


def _global_bool(values: dict[str, Any], key: str, default: bool) -> bool:
    value = values.get(key, default)
    if isinstance(value, bool):
        return value
    raise ConfigError(f"Konfiguration {key} ist ungueltig.")


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


def _app_icon(value: object) -> str:
    try:
        return normalize_icon_name(value)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc


def _optional_string(value: object, key: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ConfigError(f"Konfiguration {key} ist ungueltig.")
    return value.strip()


def _toml_basic_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_key(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return value
    return _toml_string(value)


def _clean_prompt_template(name: str, template: str) -> tuple[str, str]:
    clean_name = _clean_prompt_template_name(name)
    if not isinstance(template, str) or not template.strip():
        raise ConfigError(f"Prompt-Template '{clean_name}' braucht Text.")
    return clean_name, template.strip()


def _clean_prompt_template_name(name: str) -> str:
    clean_name = str(name).strip()
    if not clean_name:
        raise ConfigError("Prompt-Template mit leerem Namen.")
    return clean_name


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
    path_start = _secret_source_path_start(value)
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\":
            escaped.append(char)
            index += 1
            continue
        run_start = index
        while index < len(value) and value[index] == "\\":
            index += 1
        run_length = index - run_start
        if run_start == path_start and run_length == 2:
            escaped.append("\\\\\\\\")
        elif run_length % 2 == 0:
            escaped.append("\\" * run_length)
        else:
            escaped.append("\\" * (run_length + 1))
    return "".join(escaped)


def _secret_source_path_start(value: str) -> int:
    for prefix in ("envfile:", "file:"):
        if value.startswith(prefix):
            return len(prefix)
    return -1


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
