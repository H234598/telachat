from __future__ import annotations

import unittest
from importlib.resources import as_file

from telachat.assets import (
    ICON_RANDOM,
    ICON_SYSTEM,
    icon_choices,
    icon_labels,
    icon_png_resource,
    normalize_icon_name,
    random_icon_name,
)


class AssetTests(unittest.TestCase):
    def test_icon_registry_exposes_system_random_and_imported_icons(self) -> None:
        choices = icon_choices()
        labels = icon_labels()

        self.assertEqual(choices[:2], (ICON_SYSTEM, ICON_RANDOM))
        self.assertIn("01_black_cat_silhouette", choices)
        self.assertEqual(labels[ICON_SYSTEM], "System")
        self.assertEqual(labels[ICON_RANDOM], "Zufall jede Stunde")
        self.assertEqual(normalize_icon_name("zufall"), ICON_RANDOM)

    def test_icon_resource_points_to_png_asset(self) -> None:
        resource = icon_png_resource("01_black_cat_silhouette")
        with as_file(resource) as path:
            self.assertTrue(path.exists())
            self.assertEqual(path.suffix, ".png")

    def test_random_icon_returns_concrete_icon(self) -> None:
        icon = random_icon_name()
        self.assertNotIn(icon, {ICON_SYSTEM, ICON_RANDOM})
        self.assertIn(icon, icon_choices())


if __name__ == "__main__":
    unittest.main()
