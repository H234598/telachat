from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from telachat.skill_watchdog import (
    BACKUP_SUFFIX,
    compact_skill_description,
    iter_skill_files,
    run_skill_watchdog,
    start_skill_watchdog,
)


class SkillWatchdogTests(unittest.TestCase):
    def test_background_watchdog_is_opt_in(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "TELACHAT_ENABLE_SKILL_WATCHDOG": "",
                "TELACHAT_DISABLE_SKILL_WATCHDOG": "",
            },
            clear=False,
        ):
            self.assertFalse(start_skill_watchdog((Path("/missing"),)))

    def test_background_watchdog_disable_overrides_enable(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "TELACHAT_ENABLE_SKILL_WATCHDOG": "1",
                "TELACHAT_DISABLE_SKILL_WATCHDOG": "1",
            },
            clear=False,
        ):
            self.assertFalse(start_skill_watchdog((Path("/missing"),)))

    def test_compacts_oversized_frontmatter_description_and_preserves_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "skills" / "demo" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "---\n"
                "name: demo\n"
                "description: |\n"
                f"  {'x' * 1200}\n"
                "argument-hint: [input]\n"
                "---\n"
                "\n"
                "# Demo\n"
                "\n"
                "Preserved body.\n",
                encoding="utf-8",
            )

            self.assertTrue(compact_skill_description(skill))

            text = skill.read_text(encoding="utf-8")
            self.assertIn("# Demo", text)
            self.assertIn("Preserved body.", text)
            self.assertIn('description: "demo: compact Telachat-safe description.', text)
            self.assertIn("argument-hint: [input]", text)
            self.assertTrue(skill.with_name("SKILL.md" + BACKUP_SUFFIX).exists())
            description_line = next(
                line for line in text.splitlines() if line.startswith("description:")
            )
            self.assertLessEqual(len(description_line), 1024)

    def test_short_description_is_left_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "SKILL.md"
            original = "---\nname: demo\ndescription: Short.\n---\n# Demo\n"
            skill.write_text(original, encoding="utf-8")

            self.assertFalse(compact_skill_description(skill))

            self.assertEqual(skill.read_text(encoding="utf-8"), original)
            self.assertFalse(skill.with_name("SKILL.md" + BACKUP_SUFFIX).exists())

    def test_run_reports_compacted_unchanged_and_skipped_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            long_skill = root / "long" / "SKILL.md"
            short_skill = root / "short" / "SKILL.md"
            no_frontmatter = root / "plain" / "SKILL.md"
            for path in (long_skill, short_skill, no_frontmatter):
                path.parent.mkdir(parents=True)
            long_skill.write_text(
                "---\nname: long\ndescription: |\n  " + ("x" * 1100) + "\n---\n# Long\n",
                encoding="utf-8",
            )
            short_skill.write_text(
                "---\nname: short\ndescription: Short.\n---\n# Short\n",
                encoding="utf-8",
            )
            no_frontmatter.write_text("# Plain\n", encoding="utf-8")

            self.assertEqual(
                iter_skill_files((root,)),
                (long_skill, no_frontmatter, short_skill),
            )
            result = run_skill_watchdog((root,))

            self.assertEqual(result.scanned, 3)
            self.assertEqual(result.compacted, 1)
            self.assertEqual(result.unchanged, 1)
            self.assertEqual(result.skipped, 1)
            self.assertEqual(result.errors, ())


if __name__ == "__main__":
    unittest.main()
