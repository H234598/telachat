from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    "",
    ".1",
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".nsi",
    ".ps1",
    ".py",
    ".rst",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SECRET_PATTERNS = {
    "anthropic": re.compile(r"\bsk-ant-api03-[A-Za-z0-9_-]{40,}\b"),
    "github": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})\b"),
    "google": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "huggingface": re.compile(r"\bhf_[A-Za-z0-9]{32,}\b"),
    "openai": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"),
}


def _tracked_files() -> list[Path]:
    try:
        output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return [
            path
            for path in ROOT.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(ROOT).parts
        ]
    return [
        ROOT / raw.decode("utf-8")
        for raw in output.split(b"\0")
        if raw
    ]


class SecretHygieneTests(unittest.TestCase):
    def test_tracked_text_files_do_not_contain_token_shaped_secrets(self) -> None:
        failures: list[str] = []
        for path in _tracked_files():
            if path.suffix not in TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for name, pattern in SECRET_PATTERNS.items():
                for match in pattern.finditer(text):
                    line = text.count("\n", 0, match.start()) + 1
                    failures.append(f"{path.relative_to(ROOT)}:{line} looks like a {name} token")

        self.assertEqual([], failures)


if __name__ == "__main__":
    unittest.main()
