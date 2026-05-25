from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from telachat import __version__


class DocsTests(unittest.TestCase):
    def test_man_pages_exist(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for name in ("telachat.1", "telachat-tk.1", "telachat-gtk.1"):
            path = root / "docs" / "man" / name
            self.assertTrue(path.exists(), name)
            text = path.read_text(encoding="utf-8")
            self.assertIn(".SH NAME", text)

    def test_release_version_markers_are_consistent(self) -> None:
        root = Path(__file__).resolve().parents[1]
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        version = pyproject["project"]["version"]
        self.assertEqual(__version__, version)
        self.assertIn(
            f"Aktuelle Version: `{version}`",
            (root / "README.md").read_text(encoding="utf-8"),
        )
        self.assertIn(f"## {version} - ", (root / "CHANGELOG.md").read_text(encoding="utf-8"))
        self.assertIn(
            f"## {version} - ",
            (root / "docs" / "wiki" / "Releases.md").read_text(encoding="utf-8"),
        )
        for name in ("telachat.1", "telachat-tk.1", "telachat-gtk.1"):
            first_line = (
                (root / "docs" / "man" / name).read_text(encoding="utf-8").splitlines()[0]
            )
            self.assertIn(f"Telachat {version}", first_line)


if __name__ == "__main__":
    unittest.main()
