from __future__ import annotations

import unittest

from telachat.commands import slash_command_help, slash_command_suggestions


class CommandCatalogTests(unittest.TestCase):
    def test_slash_command_suggestions_match_prefixes_and_aliases(self) -> None:
        self.assertEqual(
            slash_command_suggestions("/per", limit=1)[0].name,
            "/permissions",
        )
        self.assertEqual(
            slash_command_suggestions("/ren", limit=1)[0].name,
            "/rename",
        )
        self.assertEqual(
            slash_command_suggestions("/hi", limit=1)[0].name,
            "/help",
        )

    def test_slash_command_help_contains_gui_and_cli_commands(self) -> None:
        help_text = slash_command_help()
        self.assertIn("/folder-system TEXT", help_text)
        self.assertIn("/export [datei.md]", help_text)
        self.assertIn("/provider NAME", help_text)


if __name__ == "__main__":
    unittest.main()
