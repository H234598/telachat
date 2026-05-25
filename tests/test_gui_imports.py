from __future__ import annotations

import importlib
import unittest
import warnings


class GuiImportTests(unittest.TestCase):
    def test_tk_gui_imports(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        self.assertTrue(hasattr(module, "TkTelachatApp"))

    def test_gtk_gui_imports(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        self.assertTrue(hasattr(module, "GtkTelachatApp"))


if __name__ == "__main__":
    unittest.main()
