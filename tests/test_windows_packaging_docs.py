from __future__ import annotations

import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsPackagingDocsTests(unittest.TestCase):
    def test_release_checksums_match_tracked_artifacts(self) -> None:
        release_dir = ROOT / "releases"
        checksum_files = sorted(release_dir.glob("*.sha256"))
        if not checksum_files:
            return

        failures = []
        for checksum_file in checksum_files:
            parts = checksum_file.read_text(encoding="ascii").strip().split(maxsplit=1)
            if len(parts) != 2:
                failures.append(f"{checksum_file.name} is not '<sha256>  <filename>'")
                continue
            expected, file_name = parts
            artifact = release_dir / file_name
            if not artifact.is_file():
                failures.append(f"{checksum_file.name} points to missing {file_name}")
                continue
            actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
            if actual != expected:
                failures.append(f"{checksum_file.name} expected {expected}, got {actual}")

        self.assertEqual([], failures)

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
