from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_DESCRIPTION_LIMIT = 1024
DEFAULT_INTERVAL_SECONDS = 3600
BACKUP_SUFFIX = ".telachat-watchdog.bak"

_WATCHDOG_LOCK = threading.Lock()
_WATCHDOG_STARTED = False


@dataclass(frozen=True)
class SkillWatchdogResult:
    scanned: int = 0
    compacted: int = 0
    unchanged: int = 0
    skipped: int = 0
    errors: tuple[str, ...] = field(default_factory=tuple)


def default_skill_roots(home: Path | None = None) -> tuple[Path, ...]:
    configured = os.environ.get("TELACHAT_SKILL_WATCHDOG_ROOTS", "").strip()
    if configured:
        return tuple(
            Path(item).expanduser()
            for item in configured.split(os.pathsep)
            if item.strip()
        )
    base = home or Path.home()
    codex_home = Path(os.environ.get("CODEX_HOME", base / ".codex")).expanduser()
    return (
        codex_home / "plugins" / "cache",
        codex_home / ".tmp" / "plugins" / "plugins",
        codex_home / "skills",
        base / ".agents" / "skills",
    )


def run_skill_watchdog(
    roots: tuple[Path, ...] | None = None,
    *,
    description_limit: int = DEFAULT_DESCRIPTION_LIMIT,
) -> SkillWatchdogResult:
    errors: list[str] = []
    scanned = compacted = unchanged = skipped = 0
    for skill_file in iter_skill_files(roots or default_skill_roots()):
        scanned += 1
        try:
            changed = compact_skill_description(
                skill_file,
                description_limit=description_limit,
            )
        except OSError as exc:
            errors.append(f"{skill_file}: {exc}")
            continue
        if changed is True:
            compacted += 1
        elif changed is False:
            unchanged += 1
        else:
            skipped += 1
    return SkillWatchdogResult(scanned, compacted, unchanged, skipped, tuple(errors))


def start_skill_watchdog(
    roots: tuple[Path, ...] | None = None,
    *,
    description_limit: int = DEFAULT_DESCRIPTION_LIMIT,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> bool:
    if os.environ.get("TELACHAT_DISABLE_SKILL_WATCHDOG") == "1":
        return False
    global _WATCHDOG_STARTED
    with _WATCHDOG_LOCK:
        if _WATCHDOG_STARTED:
            return False
        _WATCHDOG_STARTED = True
    thread = threading.Thread(
        target=_watchdog_loop,
        args=(roots, description_limit, interval_seconds),
        daemon=True,
        name="telachat-skill-watchdog",
    )
    thread.start()
    return True


def iter_skill_files(roots: tuple[Path, ...]) -> tuple[Path, ...]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        files.extend(
            path
            for path in root.rglob("SKILL.md")
            if path.is_file() and not path.name.endswith(BACKUP_SUFFIX)
        )
    return tuple(sorted(set(files)))


def compact_skill_description(
    path: Path,
    *,
    description_limit: int = DEFAULT_DESCRIPTION_LIMIT,
) -> bool | None:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(text)
    if frontmatter is None:
        return None
    description = _frontmatter_description(frontmatter)
    if description is None:
        return None
    if len(description) <= description_limit:
        return False
    compacted_frontmatter = _replace_description(
        frontmatter,
        _compact_description(frontmatter, description_limit),
    )
    if compacted_frontmatter == frontmatter:
        return False
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")
    path.write_text(f"---\n{compacted_frontmatter}\n---{body}", encoding="utf-8")
    return True


def _watchdog_loop(
    roots: tuple[Path, ...] | None,
    description_limit: int,
    interval_seconds: int,
) -> None:
    while True:
        run_skill_watchdog(roots, description_limit=description_limit)
        threading.Event().wait(max(60, interval_seconds))


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    marker = "\n---"
    end = text.find(marker, 4)
    if end < 0:
        return None, text
    frontmatter = text[4:end]
    body = text[end + len(marker) :]
    return frontmatter.strip("\n"), body


def _frontmatter_description(frontmatter: str) -> str | None:
    lines = frontmatter.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "description: |" or stripped == "description: >":
            values: list[str] = []
            for item in lines[index + 1 :]:
                if item and not item.startswith((" ", "\t")):
                    break
                values.append(item.strip())
            return "\n".join(values).strip()
        if stripped.startswith("description:"):
            return stripped.partition(":")[2].strip().strip("\"'")
    return None


def _replace_description(frontmatter: str, description: str) -> str:
    lines = frontmatter.splitlines()
    replacement = f'description: "{_yaml_double_quoted(description)}"'
    for index, line in enumerate(lines):
        if not line.strip().startswith("description:"):
            continue
        end = index + 1
        if line.strip() in {"description: |", "description: >"}:
            while end < len(lines) and (not lines[end] or lines[end].startswith((" ", "\t"))):
                end += 1
        return "\n".join(lines[:index] + [replacement] + lines[end:])
    return frontmatter


def _compact_description(frontmatter: str, description_limit: int) -> str:
    name = _frontmatter_scalar(frontmatter, "name") or "skill"
    text = (
        f"{name}: compact Telachat-safe description. Use when the user explicitly "
        f"asks for {name} or the matching connector capability. Prefer available "
        "app/MCP/CLI tools, inspect the preserved skill body or adjacent references "
        "only as needed, and keep secrets, tokens, raw logs, and hidden IDs out of chat."
    )
    if len(text) <= description_limit:
        return text
    return text[: max(0, description_limit - 1)].rstrip() + "."


def _frontmatter_scalar(frontmatter: str, key: str) -> str | None:
    prefix = f"{key}:"
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped.partition(":")[2].strip().strip("\"'")
    return None


def _yaml_double_quoted(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
