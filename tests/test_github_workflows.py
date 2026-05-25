from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
USES_RE = re.compile(
    r"^\s*uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([^\s#]+)",
    re.MULTILINE,
)
NODE24_MINIMUMS = {
    "actions/checkout": 5,
    "actions/setup-python": 6,
    "actions/upload-artifact": 6,
}


class GitHubWorkflowTests(unittest.TestCase):
    def test_official_actions_use_node24_compatible_majors(self) -> None:
        failures: list[str] = []
        for workflow in sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(
            WORKFLOW_DIR.glob("*.yaml")
        ):
            text = workflow.read_text(encoding="utf-8")
            for action, ref in USES_RE.findall(text):
                minimum = NODE24_MINIMUMS.get(action.lower())
                major_match = re.fullmatch(r"v(\d+)(?:\.\d+){0,2}", ref)
                if minimum is None or major_match is None:
                    continue
                major = int(major_match.group(1))
                if major < minimum:
                    failures.append(
                        f"{workflow.relative_to(ROOT)} uses {action}@{ref}; "
                        f"use {action}@v{minimum} or newer."
                    )

        self.assertEqual([], failures)

    def test_release_uploads_do_not_use_raw_globs(self) -> None:
        failures: list[str] = []
        for workflow in sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(
            WORKFLOW_DIR.glob("*.yaml")
        ):
            lines = workflow.read_text(encoding="utf-8").splitlines()
            for line_no, line in enumerate(lines, 1):
                command = line.strip()
                if not command.startswith("gh release upload "):
                    continue
                if "*" in command:
                    failures.append(
                        f"{workflow.relative_to(ROOT)}:{line_no} resolves release "
                        "assets via raw wildcards; collect and validate explicit "
                        "file paths before calling gh release upload."
                    )

        self.assertEqual([], failures)


if __name__ == "__main__":
    unittest.main()
