from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsPackagingDocsTests(unittest.TestCase):
    def test_versioned_windows_outputs_are_documented(self) -> None:
        build_script = (ROOT / "packaging/windows/build-tk-windows.ps1").read_text(
            encoding="utf-8"
        )
        if "TelachatTk-$Version-windows-x64.zip" not in build_script:
            return

        readme = (ROOT / "packaging/windows/README.md").read_text(encoding="utf-8")
        expected_outputs = [
            r"dist\TelachatTk\TelachatTk.exe",
            r"dist\TelachatTk-<version>-windows-x64.zip",
            r"dist\TelachatTk-<version>-windows-x64.zip.sha256",
            r"dist\TelachatTk-Setup-<version>.exe",
            r"dist\TelachatTk-Setup-<version>.exe.sha256",
        ]
        missing = [output for output in expected_outputs if output not in readme]

        self.assertEqual(
            [],
            missing,
            "Windows README does not document all build outputs.",
        )


if __name__ == "__main__":
    unittest.main()
