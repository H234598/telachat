from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from telachat.templates import (
    custom_template_variables,
    format_prompt_template_preview,
    is_template_variable_name,
    remember_template_values,
    render_prompt_template,
    template_value_defaults,
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

    def test_render_custom_variables_from_values(self) -> None:
        self.assertEqual(
            render_prompt_template(
                "Pruefe {topic}: {input} ({audience})",
                "  Inhalt  ",
                values={"topic": "Login", "audience": "Support"},
            ),
            "Pruefe Login: Inhalt (Support)",
        )

    def test_template_variables_only_reports_supported_names(self) -> None:
        self.assertEqual(
            template_variables("{date} {unknown} {input} {datetime}"),
            ("input", "date", "datetime"),
        )

    def test_custom_template_variables_reports_unsupported_names(self) -> None:
        self.assertEqual(
            custom_template_variables("{date} {unknown} {input} {topic} {topic}"),
            ("topic", "unknown"),
        )

    def test_template_value_history_filters_defaults_by_current_variables(self) -> None:
        history: dict[str, dict[str, str]] = {}
        remember_template_values(
            history,
            "triage",
            {"topic": "Login", "audience": "Support"},
        )

        self.assertEqual(
            template_value_defaults(history, "triage", ("topic", "missing")),
            {"topic": "Login", "missing": ""},
        )
        self.assertEqual(template_value_defaults(history, "other", ("topic",)), {"topic": ""})

    def test_is_template_variable_name_validates_placeholder_names(self) -> None:
        self.assertTrue(is_template_variable_name("topic_2"))
        self.assertFalse(is_template_variable_name("2topic"))
        self.assertFalse(is_template_variable_name("topic-name"))

    def test_format_prompt_template_preview_includes_metadata_and_text(self) -> None:
        self.assertEqual(
            format_prompt_template_preview("brief", "Kurz {input} am {date}"),
            "\n".join(
                [
                    "Name: brief",
                    "Zeichen: 22",
                    "Variablen: {input}, {date}",
                    "Custom-Variablen: keine",
                    "",
                    "Kurz {input} am {date}",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
