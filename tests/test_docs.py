from __future__ import annotations

import unittest
from pathlib import Path


class DocsTests(unittest.TestCase):
    def test_man_pages_exist(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for name in ("telachat.1", "telachat-tk.1", "telachat-gtk.1"):
            path = root / "docs" / "man" / name
            self.assertTrue(path.exists(), name)
            text = path.read_text(encoding="utf-8")
            self.assertIn(".SH NAME", text)


if __name__ == "__main__":
    unittest.main()
