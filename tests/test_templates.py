from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from telachat.templates import (
    format_prompt_template_preview,
    render_prompt_template,
    template_variables,
)


class PromptTemplateTests(unittest.TestCase):
    def test_render_builtin_variables_with_fixed_clock(self) -> None:
        now = datetime(2026, 5, 25, 9, 7, 8, tzinfo=timezone(timedelta(hours=2)))
        self.assertEqual(
            render_prompt_template("Heute {date} um {time}: {input}", "  Bericht  ", now=now),
            "Heute 2026-05-25 um 09:07: Bericht",
        )
        self.assertEqual(
            render_prompt_template("Stand: {datetime}", now=now),
            "Stand: 2026-05-25T09:07:08+02:00",
        )

    def test_templates_without_input_still_append_user_text(self) -> None:
        now = datetime(2026, 5, 25, 9, 7, 8, tzinfo=timezone.utc)
        self.assertEqual(
            render_prompt_template("Pruefe das knapp am {date}.", "  Inhalt  ", now=now),
            "Pruefe das knapp am 2026-05-25.\n\nInhalt",
        )

    def test_template_variables_only_reports_supported_names(self) -> None:
        self.assertEqual(
            template_variables("{date} {unknown} {input} {datetime}"),
            ("input", "date", "datetime"),
        )

    def test_format_prompt_template_preview_includes_metadata_and_text(self) -> None:
        self.assertEqual(
            format_prompt_template_preview("brief", "Kurz {input} am {date}"),
            "\n".join(
                [
                    "Name: brief",
                    "Zeichen: 22",
                    "Variablen: {input}, {date}",
                    "",
                    "Kurz {input} am {date}",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
