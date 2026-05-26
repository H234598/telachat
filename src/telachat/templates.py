from __future__ import annotations

import re
from datetime import datetime


SUPPORTED_TEMPLATE_VARIABLES = ("input", "date", "time", "datetime")
_VARIABLE_NAME_PATTERN = r"[A-Za-z_][A-Za-z0-9_]*"
_VARIABLE_NAME_RE = re.compile(rf"^{_VARIABLE_NAME_PATTERN}$")
_VARIABLE_RE = re.compile(r"\{(" + _VARIABLE_NAME_PATTERN + r")\}")


def is_template_variable_name(name: str) -> bool:
    return bool(_VARIABLE_NAME_RE.match(name))


def template_variables(template: str) -> tuple[str, ...]:
    found = {match.group(1) for match in _VARIABLE_RE.finditer(template)}
    return tuple(name for name in SUPPORTED_TEMPLATE_VARIABLES if name in found)


def custom_template_variables(template: str) -> tuple[str, ...]:
    found = {
        match.group(1)
        for match in _VARIABLE_RE.finditer(template)
        if match.group(1) not in SUPPORTED_TEMPLATE_VARIABLES
    }
    return tuple(sorted(found))


def template_value_defaults(
    history: dict[str, dict[str, str]],
    template_name: str,
    variables: tuple[str, ...],
) -> dict[str, str]:
    values = history.get(template_name, {})
    return {name: values.get(name, "") for name in variables}


def remember_template_values(
    history: dict[str, dict[str, str]],
    template_name: str,
    values: dict[str, str],
) -> None:
    if values:
        history[template_name] = dict(values)


def format_prompt_template_preview(name: str, template: str) -> str:
    variables = template_variables(template)
    variable_text = ", ".join("{" + variable + "}" for variable in variables) or "keine"
    custom_variables = custom_template_variables(template)
    custom_variable_text = (
        ", ".join("{" + variable + "}" for variable in custom_variables) or "keine"
    )
    return "\n".join(
        [
            f"Name: {name}",
            f"Zeichen: {len(template)}",
            f"Variablen: {variable_text}",
            f"Custom-Variablen: {custom_variable_text}",
            "",
            template,
        ]
    )


def render_prompt_template(
    template: str,
    text: str = "",
    *,
    values: dict[str, str] | None = None,
    now: datetime | None = None,
) -> str:
    clean = text.strip()
    timestamp = now or datetime.now().astimezone()
    replacements = {
        "input": clean,
        "date": timestamp.date().isoformat(),
        "time": timestamp.strftime("%H:%M"),
        "datetime": timestamp.isoformat(timespec="seconds"),
    }
    rendered = template
    for name in SUPPORTED_TEMPLATE_VARIABLES:
        rendered = rendered.replace("{" + name + "}", replacements[name])
    for name, value in sorted((values or {}).items()):
        if name not in SUPPORTED_TEMPLATE_VARIABLES:
            rendered = rendered.replace("{" + name + "}", value)
    if "input" not in template_variables(template) and clean:
        return f"{rendered}\n\n{clean}".strip()
    return rendered.strip()
