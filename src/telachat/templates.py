from __future__ import annotations

import re
from datetime import datetime


SUPPORTED_TEMPLATE_VARIABLES = ("input", "date", "time", "datetime")
_VARIABLE_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def template_variables(template: str) -> tuple[str, ...]:
    found = {match.group(1) for match in _VARIABLE_RE.finditer(template)}
    return tuple(name for name in SUPPORTED_TEMPLATE_VARIABLES if name in found)


def render_prompt_template(
    template: str,
    text: str = "",
    *,
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
    if "input" not in template_variables(template) and clean:
        return f"{rendered}\n\n{clean}".strip()
    return rendered.strip()
