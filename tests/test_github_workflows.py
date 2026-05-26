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
UNTRUSTED_RUN_CONTEXT_RE = re.compile(
    r"\$\{\{\s*(github\.event|github\.head_ref|github\.base_ref)\b"
)
NODE24_MINIMUMS = {
    "actions/checkout": 5,
    "actions/setup-python": 6,
    "actions/upload-artifact": 6,
}


def _workflow_files() -> list[Path]:
    return sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))


def _workflow_job_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    in_jobs = False

    for line in text.splitlines():
        if line == "jobs:":
            in_jobs = True
            continue
        if not in_jobs:
            continue
        if line and not line.startswith(" "):
            break

        job_match = re.fullmatch(r"  ([A-Za-z0-9_-]+):", line)
        if job_match:
            current = job_match.group(1)
            blocks[current] = []
            continue
        if current is not None:
            blocks[current].append(line)

    return {name: "\n".join(lines) for name, lines in blocks.items()}


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


def _run_blocks(lines: list[str]) -> list[tuple[int, str]]:
    blocks: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        run_match = re.match(r"^(\s*)run:\s*(.*)$", line)
        if not run_match:
            index += 1
            continue

        indent = len(run_match.group(1))
        value = run_match.group(2).strip()
        line_no = index + 1
        if value not in {"|", ">"}:
            blocks.append((line_no, value))
            index += 1
            continue

        index += 1
        block_lines: list[str] = []
        while index < len(lines):
            child = lines[index]
            if child.strip():
                child_indent = len(child) - len(child.lstrip(" "))
                if child_indent <= indent:
                    break
            block_lines.append(child)
            index += 1
        blocks.append((line_no, "\n".join(block_lines)))

    return blocks


def _checkout_steps(lines: list[str]) -> list[tuple[int, str]]:
    steps: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not re.match(r"^\s*uses:\s*actions/checkout@v5\s*$", line):
            index += 1
            continue

        step_indent = max(0, len(line) - len(line.lstrip(" ")) - 2)
        next_step = " " * step_indent + "- "
        line_no = index + 1
        block_lines = [line]
        index += 1
        while index < len(lines) and not lines[index].startswith(next_step):
            block_lines.append(lines[index])
            index += 1
        steps.append((line_no, "\n".join(block_lines)))

    return steps


class GitHubWorkflowTests(unittest.TestCase):
    def test_linux_workflow_runs_unit_checks_and_zipapp_smoke(self) -> None:
        workflow = WORKFLOW_DIR / "linux.yml"
        text = workflow.read_text(encoding="utf-8")

        self.assertIn("runs-on: ubuntu-24.04", text)
        self.assertIn("name: Workflow lint", text)
        self.assertIn("name: Shell lint", text)
        self.assertIn("sudo apt-get install -y shellcheck", text)
        self.assertIn("packaging/linux/*.sh", text)
        self.assertIn("packaging/linux/wrappers/*.in", text)
        self.assertIn('ACTIONLINT_VERSION: "1.7.12"', text)
        self.assertIn(
            'ACTIONLINT_SHA256: "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8"',
            text,
        )
        self.assertIn("sha256sum -c -", text)
        self.assertIn("run: ./actionlint", text)
        self.assertIn("      - workflow-lint", text)
        self.assertIn("      - shell-lint", text)
        self.assertIn('          - "3.11"', text)
        self.assertIn('          - "3.12"', text)
        self.assertIn("make check PYTHON=python", text)
        self.assertIn("make zipapp PYTHON=python", text)
        self.assertIn("name: Install smoke", text)
        self.assertIn("python -m pip install .", text)
        self.assertIn("telachat --version", text)
        self.assertIn("telachat profiles --json", text)
        self.assertIn("telachat config-check --json", text)
        self.assertIn("      - zipapp-smoke", text)
        self.assertIn("      - install-smoke", text)
        self.assertNotIn("${{ runner.", text)
        self.assertIn('export XDG_CONFIG_HOME="$RUNNER_TEMP/xdg-config"', text)
        self.assertIn('export XDG_DATA_HOME="$RUNNER_TEMP/xdg-data"', text)
        self.assertIn("python dist/telachat.pyz --version", text)
        self.assertIn("python dist/telachat.pyz profiles --json", text)
        self.assertIn("python dist/telachat.pyz config-check --json", text)

    def test_windows_workflow_checks_release_packaging_scripts(self) -> None:
        workflow = WORKFLOW_DIR / "windows.yml"
        text = workflow.read_text(encoding="utf-8")

        self.assertIn("name: PowerShell syntax", text)
        self.assertIn("[System.Management.Automation.Language.Parser]::ParseFile", text)
        self.assertIn(r"Get-ChildItem -Path packaging\windows -Filter *.ps1", text)
        self.assertIn("needs: powershell-syntax", text)
        self.assertIn("name: Smoke test NSIS installer script", text)
        self.assertIn("makensis /DPRODUCT_VERSION=0.0.0", text)
        self.assertIn(r"packaging\windows\telachat-tk.nsi", text)

    def test_workflow_jobs_have_timeouts(self) -> None:
        failures: list[str] = []
        for workflow in _workflow_files():
            text = workflow.read_text(encoding="utf-8")
            for job, body in _workflow_job_blocks(text).items():
                if "\n    timeout-minutes:" not in f"\n{body}":
                    failures.append(
                        f"{workflow.relative_to(ROOT)} job {job} has no timeout-minutes."
                    )

        self.assertEqual([], failures)

    def test_checkout_steps_do_not_persist_credentials(self) -> None:
        failures: list[str] = []
        for workflow in _workflow_files():
            lines = workflow.read_text(encoding="utf-8").splitlines()
            for line_no, block in _checkout_steps(lines):
                if "persist-credentials: false" not in block:
                    failures.append(
                        f"{workflow.relative_to(ROOT)}:{line_no} leaves checkout "
                        "credentials persisted for later steps."
                    )

        self.assertEqual([], failures)

    def test_workflows_use_anonymous_public_fetch_checkout(self) -> None:
        failures: list[str] = []
        for workflow in _workflow_files():
            text = workflow.read_text(encoding="utf-8")
            if "uses: actions/checkout@" in text:
                failures.append(
                    f"{workflow.relative_to(ROOT)} still uses token-backed checkout."
                )
            if (
                'git -c protocol.version=2 fetch --no-tags --prune --depth=1 origin "+${GITHUB_REF}:refs/remotes/origin/checkout"'
                not in text
            ):
                failures.append(
                    f"{workflow.relative_to(ROOT)} does not fetch the triggering ref "
                    "through anonymous public Git."
                )
            if 'git checkout --force --detach "${GITHUB_SHA}"' not in text:
                failures.append(
                    f"{workflow.relative_to(ROOT)} does not detach at the triggering SHA."
                )

        self.assertEqual([], failures)

    def test_workflows_avoid_untrusted_trigger_contexts_in_scripts(self) -> None:
        failures: list[str] = []
        for workflow in _workflow_files():
            text = workflow.read_text(encoding="utf-8")
            if re.search(r"^\s*pull_request_target\s*:", text, re.MULTILINE):
                failures.append(
                    f"{workflow.relative_to(ROOT)} uses pull_request_target; prefer "
                    "pull_request with read-only permissions for untrusted changes."
                )
            for line_no, script in _run_blocks(text.splitlines()):
                match = UNTRUSTED_RUN_CONTEXT_RE.search(script)
                if match:
                    failures.append(
                        f"{workflow.relative_to(ROOT)}:{line_no} interpolates "
                        f"{match.group(1)} directly into a run script."
                    )

        self.assertEqual([], failures)

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
