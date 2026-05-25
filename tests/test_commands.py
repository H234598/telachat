from __future__ import annotations

import unittest
from types import SimpleNamespace

from telachat.commands import (
    SLASH_COMMANDS,
    canonical_slash_command,
    estimate_context,
    format_context_lines,
    format_context_summary,
    format_message_matches,
    format_stats_lines,
    format_stats_summary,
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
        self.assertIn("/models [live]", help_text)
        self.assertIn("/theme [NAME]", help_text)
        self.assertIn("/find TEXT", help_text)
        self.assertIn("/stats", help_text)
        self.assertIn("/context", help_text)
        self.assertIn("/doctor", help_text)

    def test_command_name_suggestions_include_aliases(self) -> None:
        self.assertIn("/permissions", slash_command_name_suggestions("/per"))
        self.assertIn("/theme", slash_command_name_suggestions("/the"))
        self.assertIn("/stats", slash_command_name_suggestions("/sta"))
        self.assertIn("/models", slash_command_name_suggestions("/mod"))
        self.assertIn("/doctor", slash_command_name_suggestions("/doc"))
        self.assertIn("/edit", slash_command_name_suggestions("/ed"))
        self.assertIn("/quit", slash_command_name_suggestions("/qu"))
        self.assertEqual(canonical_slash_command("/ablegen"), "/move")
        self.assertEqual(canonical_slash_command("/edit"), "/edit-last")

    def test_declared_aliases_resolve_to_canonical_commands(self) -> None:
        for command in SLASH_COMMANDS:
            self.assertEqual(canonical_slash_command(command.name), command.name)
            for alias in command.aliases:
                with self.subTest(alias=alias):
                    self.assertEqual(canonical_slash_command(alias), command.name)

        self.assertEqual(canonical_slash_command("/unknown"), "/unknown")

    def test_context_estimate_is_content_free(self) -> None:
        messages = [
            SimpleNamespace(content="Geheimer Projektplan"),
            SimpleNamespace(content="Antwort"),
        ]

        estimate = estimate_context(messages, "System", max_history_messages=1)

        self.assertEqual(estimate.messages_total, 2)
        self.assertEqual(estimate.history_messages, 1)
        self.assertEqual(estimate.system_chars, 6)
        self.assertEqual(estimate.history_chars, 7)
        self.assertEqual(estimate.total_chars, 13)
        self.assertEqual(estimate.approx_tokens, 4)
        text = "\n".join(format_context_lines(estimate))
        self.assertIn("1 im naechsten Request", text)
        self.assertIn("History-Limit: 1", text)
        self.assertNotIn("Geheimer Projektplan", text)
        self.assertEqual(format_context_summary(estimate), "Kontext ca. 4 Tokens | 1/2 Nachrichten")

    def test_stats_formatting_is_content_free(self) -> None:
        stats = SimpleNamespace(
            database_path="/tmp/history.sqlite3",
            sessions_total=2,
            sessions_active=1,
            sessions_archived=1,
            sessions_pinned=1,
            sessions_unfiled=1,
            folders_total=1,
            folders_with_system_prompt=0,
            tags_total=1,
            tag_links_total=2,
            tagged_sessions=2,
            messages_total=4,
            message_roles=(("assistant", 2), ("user", 2)),
            session_profiles=(("tki", 2),),
            session_models=(("", 2),),
        )

        lines = format_stats_lines(stats, include_database=False)

        self.assertEqual(
            format_stats_summary(stats),
            "Sessions 2 | Nachrichten 4 | Ordner 1 | Tags 1",
        )
        self.assertNotIn("SQLite:", "\n".join(lines))
        self.assertIn("Sessions: 2 gesamt, 1 aktiv, 1 archiviert", lines[0])
        self.assertIn("assistant=2", lines[1])
        self.assertIn("Modelle: ohne Modell=2", lines[-1])

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
