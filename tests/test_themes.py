from __future__ import annotations

import unittest
from dataclasses import fields

from telachat.themes import normalize_theme_name, theme_by_name, theme_choices, theme_labels


class ThemeTests(unittest.TestCase):
    def test_theme_choices_have_labels_and_complete_hex_palettes(self) -> None:
        choices = theme_choices()
        self.assertEqual(("system", "light", "dark", "high-contrast"), choices)
        self.assertEqual(set(theme_labels()), set(choices))
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
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_theme_name(raw), expected)

    def test_unknown_theme_error_mentions_available_choices(self) -> None:
        with self.assertRaises(ValueError) as raised:
            normalize_theme_name("neon")
        message = str(raised.exception)
        self.assertIn("neon", message)
        self.assertIn("system", message)
        self.assertIn("high-contrast", message)


if __name__ == "__main__":
    unittest.main()
