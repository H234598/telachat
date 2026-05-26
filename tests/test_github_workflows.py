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
WINDOWS_LATEST_RE = re.compile(r"^\s*runs-on:\s*windows-latest\s*$", re.MULTILINE)
NODE24_MINIMUMS = {
    "actions/checkout": 5,
    "actions/setup-python": 6,
    "actions/upload-artifact": 6,
}


def _workflow_files() -> list[Path]:
    return sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))


def _release_upload_commands(lines: list[str]) -> list[tuple[int, str]]:
    commands: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        command = lines[index].strip()
        line_no = index + 1
        if not command.startswith("gh release upload "):
            index += 1
            continue
        while command.endswith("`") and index + 1 < len(lines):
            command = command[:-1].rstrip() + " " + lines[index + 1].strip()
            index += 1
        commands.append((line_no, command))
        index += 1
    return commands


class GitHubWorkflowTests(unittest.TestCase):
    def test_windows_workflows_use_explicit_runner_images(self) -> None:
        failures: list[str] = []
        for workflow in _workflow_files():
            text = workflow.read_text(encoding="utf-8")
            if WINDOWS_LATEST_RE.search(text):
                failures.append(
                    f"{workflow.relative_to(ROOT)} uses windows-latest; pin a "
                    "specific Windows runner to avoid hosted-image migrations."
                )

        self.assertEqual([], failures)

    def test_official_actions_use_node24_compatible_majors(self) -> None:
        failures: list[str] = []
        for workflow in _workflow_files():
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
        for workflow in _workflow_files():
            lines = workflow.read_text(encoding="utf-8").splitlines()
            for line_no, command in _release_upload_commands(lines):
                if "*" in command:
                    failures.append(
                        f"{workflow.relative_to(ROOT)}:{line_no} resolves release "
                        "assets via raw wildcards; collect and validate explicit "
                        "file paths before calling gh release upload."
                    )

        self.assertEqual([], failures)

    def test_release_upload_guard_follows_powershell_continuations(self) -> None:
        commands = _release_upload_commands(
            [
                "          gh release upload $Tag `",
                "            dist\\TelachatTk-*-windows-x64.zip `",
                "            --clobber",
            ]
        )

        self.assertEqual(
            commands,
            [(1, "gh release upload $Tag dist\\TelachatTk-*-windows-x64.zip --clobber")],
        )


if __name__ == "__main__":
    unittest.main()
