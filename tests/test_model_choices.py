from __future__ import annotations

import unittest

from telachat.model_choices import merge_model_choices


class ModelChoiceTests(unittest.TestCase):
    def test_merge_model_choices_keeps_selection_first_and_dedupes(self) -> None:
        self.assertEqual(
            merge_model_choices(
                "configured-b",
                ["live-a", "configured-b", "live-c"],
                ["configured-a", "configured-b"],
            ),
            ["configured-b", "live-a", "live-c", "configured-a"],
        )

    def test_merge_model_choices_handles_empty_selection(self) -> None:
        self.assertEqual(
            merge_model_choices("", ["live-a"], ["configured-a"]),
            ["live-a", "configured-a"],
        )


if __name__ == "__main__":
    unittest.main()
