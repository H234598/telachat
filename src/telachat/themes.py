from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemePalette:
    bg: str
    panel: str
    surface: str
    text: str
    muted: str
    accent: str
    accent_fg: str
    border: str
    user_bg: str
    assistant_bg: str
    input_bg: str
    selection: str
    selection_fg: str
    sash: str


@dataclass(frozen=True)
class Theme:
    name: str
    label: str
    adw_scheme: str
    palette: ThemePalette


THEMES: dict[str, Theme] = {
    "system": Theme(
        name="system",
        label="System",
        adw_scheme="default",
        palette=ThemePalette(
            bg="#f7f8f6",
            panel="#e9eee9",
            surface="#ffffff",
            text="#1f2428",
            muted="#59636b",
            accent="#0f766e",
            accent_fg="#ffffff",
            border="#c9d4d1",
            user_bg="#dff3ee",
            assistant_bg="#fff1d6",
            input_bg="#ffffff",
            selection="#0f766e",
            selection_fg="#ffffff",
            sash="#c8d1cb",
        ),
    ),
    "light": Theme(
        name="light",
        label="Light",
        adw_scheme="light",
        palette=ThemePalette(
            bg="#f7f8f6",
            panel="#e9eee9",
            surface="#ffffff",
            text="#1f2428",
            muted="#59636b",
            accent="#0f766e",
            accent_fg="#ffffff",
            border="#c9d4d1",
            user_bg="#dff3ee",
            assistant_bg="#fff1d6",
            input_bg="#ffffff",
            selection="#0f766e",
            selection_fg="#ffffff",
            sash="#c8d1cb",
        ),
    ),
    "dark": Theme(
        name="dark",
        label="Dark",
        adw_scheme="dark",
        palette=ThemePalette(
            bg="#171a1c",
            panel="#202428",
            surface="#24272b",
            text="#f0eee6",
            muted="#a7b0ad",
            accent="#37c99b",
            accent_fg="#071311",
            border="#3c4446",
            user_bg="#123b3a",
            assistant_bg="#3a2e20",
            input_bg="#111416",
            selection="#37c99b",
            selection_fg="#071311",
            sash="#30383a",
        ),
    ),
    "high-contrast": Theme(
        name="high-contrast",
        label="High Contrast",
        adw_scheme="dark",
        palette=ThemePalette(
            bg="#000000",
            panel="#050505",
            surface="#101010",
            text="#ffffff",
            muted="#e0e0e0",
            accent="#ffe900",
            accent_fg="#000000",
            border="#ffffff",
            user_bg="#002f6c",
            assistant_bg="#3b2600",
            input_bg="#000000",
            selection="#ffe900",
            selection_fg="#000000",
            sash="#ffffff",
        ),
    ),
}

THEME_ALIASES = {
    "": "system",
    "auto": "system",
    "default": "system",
    "os": "system",
    "contrast": "high-contrast",
    "highcontrast": "high-contrast",
    "hc": "high-contrast",
}


def normalize_theme_name(value: object) -> str:
    raw = str(value or "system").strip().lower().replace("_", "-")
    name = THEME_ALIASES.get(raw, raw)
    if name not in THEMES:
        available = ", ".join(theme_choices())
        raise ValueError(f"Unbekanntes Theme '{value}'. Verfuegbar: {available}")
    return name


def theme_choices() -> tuple[str, ...]:
    return tuple(THEMES)


def theme_labels() -> dict[str, str]:
    return {name: theme.label for name, theme in THEMES.items()}


def theme_by_name(value: object) -> Theme:
    return THEMES[normalize_theme_name(value)]
