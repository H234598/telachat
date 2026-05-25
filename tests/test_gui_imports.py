from __future__ import annotations

import importlib
import unittest
import warnings
from types import SimpleNamespace


class _FakeController:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def list_sessions(self, limit: int, **kwargs: object) -> list[object]:
        self.calls.append({"limit": limit, **kwargs})
        return []


class _FakeList:
    def delete(self, *_args: object) -> None:
        return None

    def get_row_at_index(self, _index: int) -> object | None:
        return None


class _FakeText:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def get_text(self) -> str:
        return self.value


class GuiImportTests(unittest.TestCase):
    def test_tk_gui_imports(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        self.assertTrue(hasattr(module, "TkTelachatApp"))

    def test_gtk_gui_imports(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            module = importlib.import_module("telachat.gtkgui")
        self.assertTrue(hasattr(module, "GtkTelachatApp"))

    def test_tk_refresh_sessions_uses_selected_archive_filter(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        controller = _FakeController()
        app = SimpleNamespace(
            controller=controller,
            session_list=_FakeList(),
            sort_keys={"Neueste zuerst": "updated_desc"},
            sort_var=_FakeText("Neueste zuerst"),
            search_var=_FakeText("Archiv"),
            selected_folder_id=lambda: "__all__",
            selected_archive_filter=lambda: "archived",
        )

        module.TkTelachatApp.refresh_sessions(app)

        self.assertEqual(controller.calls[0]["archive"], "archived")
        self.assertEqual(controller.calls[0]["folder_id"], "__all__")
        self.assertEqual(controller.calls[0]["query"], "Archiv")

    def test_gtk_refresh_sessions_uses_selected_archive_filter(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            module = importlib.import_module("telachat.gtkgui")
        controller = _FakeController()
        app = SimpleNamespace(
            controller=controller,
            session_list=_FakeList(),
            search_entry=_FakeText("Archiv"),
            selected_folder_id=lambda: "__none__",
            selected_sort=lambda: "title_asc",
            selected_archive_filter=lambda: "all",
        )

        module.GtkTelachatApp.refresh_sessions(app)

        self.assertEqual(controller.calls[0]["archive"], "all")
        self.assertEqual(controller.calls[0]["folder_id"], "__none__")
        self.assertEqual(controller.calls[0]["sort"], "title_asc")


if __name__ == "__main__":
    unittest.main()
