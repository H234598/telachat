from __future__ import annotations

import unittest

from telachat.commands import (
    canonical_slash_command,
    format_message_matches,
    slash_command_help,
    slash_command_name_suggestions,
    slash_command_suggestions,
)
from telachat.store import Message


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
        self.assertIn("/edit-last TEXT", help_text)
        self.assertIn("/fork [TITLE]", help_text)
        self.assertIn("/export [datei.md]", help_text)
        self.assertIn("/provider NAME", help_text)
        self.assertIn("/theme [NAME]", help_text)
        self.assertIn("/find TEXT", help_text)

    def test_command_name_suggestions_include_aliases(self) -> None:
        self.assertIn("/permissions", slash_command_name_suggestions("/per"))
        self.assertIn("/theme", slash_command_name_suggestions("/the"))
        self.assertIn("/edit", slash_command_name_suggestions("/ed"))
        self.assertIn("/quit", slash_command_name_suggestions("/qu"))
        self.assertEqual(canonical_slash_command("/ablegen"), "/move")
        self.assertEqual(canonical_slash_command("/edit"), "/edit-last")

    def test_message_match_formatting_is_compact(self) -> None:
        messages = [
            Message(id=1, session_id="s", role="user", content="Hallo Welt", created_at=1),
            Message(id=2, session_id="s", role="assistant", content="Keine Sache", created_at=2),
            Message(id=3, session_id="s", role="assistant", content="Welt " * 80, created_at=3),
        ]
        matches = format_message_matches(messages, "welt", width=24)
        self.assertEqual(matches[0], "1. Du: Hallo Welt")
        self.assertTrue(matches[1].startswith("3. KI: Welt Welt"))
        self.assertTrue(matches[1].endswith("..."))


if __name__ == "__main__":
    unittest.main()
