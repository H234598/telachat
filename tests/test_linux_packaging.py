from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LinuxPackagingTests(unittest.TestCase):
    def test_even_minor_tags_build_periodic_packages(self) -> None:
        def output(tag: str) -> str:
            return subprocess.run(
                ["python3", "packaging/linux/package-cadence.py", tag],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip()

        self.assertEqual(output("v0.54.0"), "build_periodic=true")
        self.assertEqual(output("0.56.2"), "build_periodic=true")
        self.assertEqual(output("v0.53.0"), "build_periodic=false")
        self.assertEqual(output("not-a-version"), "build_periodic=false")

    @unittest.skipIf(os.name == "nt", "Linux shell launchers are not executable on Windows")
    def test_installer_installs_zipapp_launchers_desktop_file_and_icon(self) -> None:
        subprocess.run(["make", "zipapp"], cwd=ROOT, check=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prefix = root / "prefix"
            desktop = root / "Desktop"
            env = os.environ.copy()
            env["XDG_CONFIG_HOME"] = str(root / "config")
            env["XDG_DATA_HOME"] = str(root / "data")
            subprocess.run(
                [
                    "sh",
                    "packaging/linux/install-telachat.sh",
                    "--prefix",
                    str(prefix),
                    "--desktop-dir",
                    str(desktop),
                    "--zipapp",
                    "dist/telachat.pyz",
                ],
                cwd=ROOT,
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertTrue((prefix / "lib/telachat/telachat.pyz").is_file())
            self.assertTrue((prefix / "bin/telachat").is_file())
            self.assertTrue((prefix / "bin/telachat-tk").is_file())
            self.assertTrue((prefix / "bin/telachat-gtk").is_file())
            self.assertTrue((prefix / "bin/telachat-gui").is_file())
            self.assertTrue((prefix / "share/applications/telachat.desktop").is_file())
            self.assertTrue((desktop / "Telachat.desktop").is_file())
            self.assertTrue(
                (prefix / "share/icons/hicolor/256x256/apps/telachat.png").is_file()
            )

            version = subprocess.run(
                [str(prefix / "bin/telachat"), "--version"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout
            self.assertIn("telachat 0.61.0", version)
            launcher = (prefix / "bin/telachat-tk").read_text(encoding="utf-8")
            self.assertIn(str(prefix / "lib/telachat/telachat.pyz"), launcher)
            desktop_text = (desktop / "Telachat.desktop").read_text(encoding="utf-8")
            self.assertIn("Type=Application", desktop_text)
            self.assertIn("Icon=telachat", desktop_text)
            self.assertIn(f"Exec={prefix}/bin/", desktop_text)

    def test_packaging_files_are_present_for_periodic_release_artifacts(self) -> None:
        self.assertTrue((ROOT / "packaging/rpm/telachat.spec").is_file())
        self.assertTrue((ROOT / "snap/snapcraft.yaml").is_file())
        self.assertTrue((ROOT / "packaging/linux/build-rpm.sh").is_file())
        if shutil.which("rpmbuild") is None:
            self.skipTest("rpmbuild is not installed")
        result = subprocess.run(
            ["packaging/linux/build-rpm.sh"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            self.fail(
                "RPM build failed\n\nSTDOUT:\n"
                f"{result.stdout}\n\nSTDERR:\n{result.stderr}"
            )
        rpm_root = ROOT / "dist/rpm/RPMS"
        self.assertTrue(any(rpm_root.rglob("telachat-0.61.0-*.noarch.rpm")))

    def test_snapcraft_wrappers_keep_runtime_snap_mount_variable(self) -> None:
        snapcraft = (ROOT / "snap/snapcraft.yaml").read_text(encoding="utf-8")
        self.assertIn(r"\$SNAP/lib/telachat/telachat.pyz", snapcraft)
        self.assertNotIn("|$SNAP/lib/telachat/telachat.pyz|g", snapcraft)


if __name__ == "__main__":
    unittest.main()
