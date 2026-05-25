from __future__ import annotations

import unittest
from dataclasses import fields
from unittest import mock

from telachat.themes import (
    detect_system_theme,
    normalize_theme_name,
    theme_by_name,
    theme_choices,
    theme_labels,
)


class ThemeTests(unittest.TestCase):
    def test_theme_choices_have_labels_and_complete_hex_palettes(self) -> None:
        choices = theme_choices()
        self.assertEqual(
            (
                "system",
                "light",
                "dark",
                "high-contrast",
                "solarized-light",
                "solarized-dark",
                "nord",
                "dracula",
                "gruvbox",
                "ocean",
                "forest",
                "rose",
            ),
            choices,
        )
        self.assertEqual(set(theme_labels()), set(choices))
        with mock.patch.dict("os.environ", {}, clear=True):
            for name in choices:
                theme = theme_by_name(name)
                self.assertEqual(theme.name, name)
                self.assertTrue(theme.label)
                for field in fields(theme.palette):
                    value = getattr(theme.palette, field.name)
                    self.assertRegex(value, r"^#[0-9a-fA-F]{6}$", field.name)

    def test_theme_aliases_normalize_to_canonical_names(self) -> None:
        cases = {
            None: "system",
            "": "system",
            " AUTO ": "system",
            "os": "system",
            "highcontrast": "high-contrast",
            "high_contrast": "high-contrast",
            "hc": "high-contrast",
            "DARK": "dark",
            "solarized_dark": "solarized-dark",
            "solarized": "solarized-light",
            "gruvbox-dark": "gruvbox",
            "oceanic": "ocean",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_theme_name(raw), expected)

    def test_system_theme_detection_uses_environment_hints(self) -> None:
        self.assertEqual(detect_system_theme({}), "light")
        self.assertEqual(detect_system_theme({"GTK_THEME": "Adwaita:dark"}), "dark")
        self.assertEqual(detect_system_theme({"GTK_THEME": "HighContrast"}), "high-contrast")
        self.assertEqual(detect_system_theme({"COLORFGBG": "15;0"}), "dark")
        self.assertEqual(detect_system_theme({"COLORFGBG": "0;15"}), "light")
        self.assertEqual(
            detect_system_theme({"TELACHAT_SYSTEM_THEME": "solarized_dark"}),
            "solarized-dark",
        )
        self.assertEqual(
            detect_system_theme(
                {
                    "TELACHAT_SYSTEM_THEME": "rose",
                    "GTK_THEME": "Adwaita:dark",
                }
            ),
            "rose",
        )

    def test_system_theme_keeps_system_name_but_uses_detected_palette(self) -> None:
        with mock.patch.dict("os.environ", {"GTK_THEME": "Adwaita:dark"}, clear=True):
            self.assertEqual(theme_by_name("system").name, "system")
            self.assertEqual(theme_by_name("system").palette, theme_by_name("dark").palette)
        with mock.patch.dict(
            "os.environ",
            {"TELACHAT_SYSTEM_THEME": "dracula", "GTK_THEME": "Adwaita"},
            clear=True,
        ):
            self.assertEqual(theme_by_name("system").name, "system")
            self.assertEqual(theme_by_name("system").palette, theme_by_name("dracula").palette)

    def test_unknown_theme_error_mentions_available_choices(self) -> None:
        with self.assertRaises(ValueError) as raised:
            normalize_theme_name("neon")
        message = str(raised.exception)
        self.assertIn("neon", message)
        self.assertIn("system", message)
        self.assertIn("high-contrast", message)


if __name__ == "__main__":
    unittest.main()
