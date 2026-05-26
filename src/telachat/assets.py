from __future__ import annotations

import random
from importlib.resources import files
from importlib.resources.abc import Traversable


ICON_SYSTEM = "system"
ICON_RANDOM = "random"
ICON_SPECIAL_CHOICES = (ICON_SYSTEM, ICON_RANDOM)
_ICON_PNG_DIR = ("assets", "icons-png")


def icon_names() -> tuple[str, ...]:
    try:
        root = _resource_dir(_ICON_PNG_DIR)
        names = [
            item.name.removesuffix(".png")
            for item in root.iterdir()
            if item.is_file() and item.name.endswith(".png")
        ]
    except (FileNotFoundError, ModuleNotFoundError, NotADirectoryError):
        return ()
    return tuple(sorted(names))


def icon_choices() -> tuple[str, ...]:
    return (*ICON_SPECIAL_CHOICES, *icon_names())


def icon_labels() -> dict[str, str]:
    labels = {
        ICON_SYSTEM: "System",
        ICON_RANDOM: "Zufall jede Stunde",
    }
    for name in icon_names():
        labels[name] = _title_from_asset_name(name)
    return labels


def normalize_icon_name(value: object) -> str:
    raw = str(value or ICON_SYSTEM).strip()
    if not raw:
        return ICON_SYSTEM
    lowered = raw.lower().replace(" ", "_")
    aliases = {
        "default": ICON_SYSTEM,
        "none": ICON_SYSTEM,
        "system": ICON_SYSTEM,
        "zufall": ICON_RANDOM,
        "random": ICON_RANDOM,
        "random_hourly": ICON_RANDOM,
    }
    candidate = aliases.get(lowered, lowered)
    if candidate in icon_choices():
        return candidate
    available = ", ".join(icon_choices())
    raise ValueError(f"Unbekanntes App-Icon: {raw}. Verfuegbar: {available}")


def random_icon_name(previous: str | None = None) -> str:
    names = list(icon_names())
    if previous in names and len(names) > 1:
        names.remove(previous)
    if not names:
        return ICON_SYSTEM
    return random.choice(names)


def icon_png_resource(name: str) -> Traversable:
    normalized = normalize_icon_name(name)
    if normalized in ICON_SPECIAL_CHOICES:
        raise ValueError(f"Kein konkretes Icon: {normalized}")
    return _resource_dir(_ICON_PNG_DIR).joinpath(f"{normalized}.png")


def _resource_dir(parts: tuple[str, ...]) -> Traversable:
    current = files("telachat")
    for part in parts:
        current = current.joinpath(part)
    return current


def _title_from_asset_name(name: str) -> str:
    raw = name
    if len(raw) > 3 and raw[:2].isdigit() and raw[2] == "_":
        raw = raw[3:]
    return raw.replace("_", " ").strip().title()
