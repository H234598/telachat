from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "packaging" / "windows" / "build-tk-windows.ps1"


class WindowsPackagingTests(unittest.TestCase):
    def test_pyinstaller_collects_telachat_package_data(self) -> None:
        text = BUILD_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("--collect-data telachat", text)
        self.assertIn("telachat\\assets\\icons-png", text)
        self.assertIn("PyInstaller did not bundle telachat icon PNG assets", text)


if __name__ == "__main__":
    unittest.main()
