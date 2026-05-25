from __future__ import annotations

import os
from collections.abc import Mapping
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
    "solarized-light": Theme(
        name="solarized-light",
        label="Solarized Light",
        adw_scheme="light",
        palette=ThemePalette(
            bg="#fdf6e3",
            panel="#eee8d5",
            surface="#fffff4",
            text="#073642",
            muted="#657b83",
            accent="#268bd2",
            accent_fg="#ffffff",
            border="#d8cfb5",
            user_bg="#d9f0ee",
            assistant_bg="#f7e6bd",
            input_bg="#fffaf0",
            selection="#268bd2",
            selection_fg="#ffffff",
            sash="#d5cbb0",
        ),
    ),
    "solarized-dark": Theme(
        name="solarized-dark",
        label="Solarized Dark",
        adw_scheme="dark",
        palette=ThemePalette(
            bg="#002b36",
            panel="#073642",
            surface="#0b3a46",
            text="#eee8d5",
            muted="#93a1a1",
            accent="#2aa198",
            accent_fg="#001f27",
            border="#31515a",
            user_bg="#16484f",
            assistant_bg="#4a3d16",
            input_bg="#00212a",
            selection="#2aa198",
            selection_fg="#001f27",
            sash="#254952",
        ),
    ),
    "nord": Theme(
        name="nord",
        label="Nord",
        adw_scheme="dark",
        palette=ThemePalette(
            bg="#2e3440",
            panel="#3b4252",
            surface="#434c5e",
            text="#eceff4",
            muted="#d8dee9",
            accent="#88c0d0",
            accent_fg="#1f252f",
            border="#4c566a",
            user_bg="#35535b",
            assistant_bg="#514a35",
            input_bg="#242933",
            selection="#88c0d0",
            selection_fg="#1f252f",
            sash="#4c566a",
        ),
    ),
    "dracula": Theme(
        name="dracula",
        label="Dracula",
        adw_scheme="dark",
        palette=ThemePalette(
            bg="#282a36",
            panel="#343746",
            surface="#3c4052",
            text="#f8f8f2",
            muted="#c7c9d1",
            accent="#ff79c6",
            accent_fg="#241423",
            border="#565b70",
            user_bg="#264858",
            assistant_bg="#4a3c55",
            input_bg="#1f212b",
            selection="#bd93f9",
            selection_fg="#21152d",
            sash="#565b70",
        ),
    ),
    "gruvbox": Theme(
        name="gruvbox",
        label="Gruvbox",
        adw_scheme="dark",
        palette=ThemePalette(
            bg="#282828",
            panel="#32302f",
            surface="#3c3836",
            text="#fbf1c7",
            muted="#d5c4a1",
            accent="#b8bb26",
            accent_fg="#1d2021",
            border="#665c54",
            user_bg="#264c3a",
            assistant_bg="#4b3f24",
            input_bg="#1d2021",
            selection="#fabd2f",
            selection_fg="#1d2021",
            sash="#504945",
        ),
    ),
    "ocean": Theme(
        name="ocean",
        label="Ocean",
        adw_scheme="dark",
        palette=ThemePalette(
            bg="#102027",
            panel="#17313a",
            surface="#1f3f49",
            text="#e6f4f1",
            muted="#a7c4c2",
            accent="#4dd0e1",
            accent_fg="#062027",
            border="#335861",
            user_bg="#155464",
            assistant_bg="#314b36",
            input_bg="#0c1b21",
            selection="#4dd0e1",
            selection_fg="#062027",
            sash="#335861",
        ),
    ),
    "forest": Theme(
        name="forest",
        label="Forest",
        adw_scheme="dark",
        palette=ThemePalette(
            bg="#17211b",
            panel="#203126",
            surface="#2a3d30",
            text="#eef5e8",
            muted="#b7c7b0",
            accent="#8bc34a",
            accent_fg="#142012",
            border="#435743",
            user_bg="#254d3d",
            assistant_bg="#4b3f2a",
            input_bg="#111a14",
            selection="#8bc34a",
            selection_fg="#142012",
            sash="#435743",
        ),
    ),
    "rose": Theme(
        name="rose",
        label="Rose",
        adw_scheme="light",
        palette=ThemePalette(
            bg="#fff7f5",
            panel="#f4e3df",
            surface="#ffffff",
            text="#302124",
            muted="#7b6268",
            accent="#c2416b",
            accent_fg="#ffffff",
            border="#dfc4c5",
            user_bg="#e2f3ed",
            assistant_bg="#f8dfdf",
            input_bg="#fffefe",
            selection="#c2416b",
            selection_fg="#ffffff",
            sash="#dfc4c5",
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
    "lightmode": "light",
    "darkmode": "dark",
    "solarized": "solarized-light",
    "solarizedlight": "solarized-light",
    "solarizeddark": "solarized-dark",
    "solarized-dark-mode": "solarized-dark",
    "gruvbox-dark": "gruvbox",
    "oceanic": "ocean",
}


def detect_system_theme(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    explicit = env.get("TELACHAT_SYSTEM_THEME")
    if explicit:
        normalized = normalize_theme_name(explicit)
        return "light" if normalized == "system" else normalized

    joined = " ".join(
        env.get(key, "").lower()
        for key in (
            "GTK_THEME",
            "QT_STYLE_OVERRIDE",
            "XDG_CURRENT_DESKTOP_THEME",
            "COLOR_SCHEME",
            "PREFERRED_COLOR_SCHEME",
        )
    )
    if "highcontrast" in joined or "high-contrast" in joined:
        return "high-contrast"
    if "dark" in joined:
        return "dark"
    if "light" in joined:
        return "light"

    colorfgbg = env.get("COLORFGBG", "")
    if colorfgbg:
        background = colorfgbg.split(";")[-1]
        try:
            color_index = int(background)
        except ValueError:
            color_index = -1
        if 0 <= color_index <= 6 or color_index == 8:
            return "dark"
        if color_index >= 7:
            return "light"

    return "light"


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
    name = normalize_theme_name(value)
    if name == "system":
        detected = detect_system_theme()
        base = THEMES.get(detected, THEMES["light"])
        return Theme(
            name="system",
            label=THEMES["system"].label,
            adw_scheme="default",
            palette=base.palette,
        )
    return THEMES[name]
