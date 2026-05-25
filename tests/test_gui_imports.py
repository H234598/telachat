from __future__ import annotations

import importlib
import unittest
import warnings
from types import SimpleNamespace


class _FakeController:
    def __init__(self, tags: list[tuple[str, int]] | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.tags = tags or []

    def list_sessions(self, limit: int, **kwargs: object) -> list[object]:
        self.calls.append({"limit": limit, **kwargs})
        return []

    def list_tags(self) -> list[tuple[str, int]]:
        return self.tags


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

    def set(self, value: str) -> None:
        self.value = value


class _FakeCombo:
    def __init__(self) -> None:
        self.values: list[str] = []

    def configure(self, **kwargs: object) -> None:
        self.values = list(kwargs.get("values", ()))


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

    def test_tk_refresh_sessions_uses_selected_sidebar_filters(self) -> None:
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
            selected_tag_filter=lambda: "projekt",
        )

        module.TkTelachatApp.refresh_sessions(app)

        self.assertEqual(controller.calls[0]["archive"], "archived")
        self.assertEqual(controller.calls[0]["folder_id"], "__all__")
        self.assertEqual(controller.calls[0]["query"], "Archiv")
        self.assertEqual(controller.calls[0]["tag"], "projekt")

    def test_gtk_refresh_sessions_uses_selected_sidebar_filters(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        controller = _FakeController()
        app = SimpleNamespace(
            controller=controller,
            session_list=_FakeList(),
            search_entry=_FakeText("Archiv"),
            selected_folder_id=lambda: "__none__",
            selected_sort=lambda: "title_asc",
            selected_archive_filter=lambda: "all",
            selected_tag_filter=lambda: "review",
        )

        module.GtkTelachatApp.refresh_sessions(app)

        self.assertEqual(controller.calls[0]["archive"], "all")
        self.assertEqual(controller.calls[0]["folder_id"], "__none__")
        self.assertEqual(controller.calls[0]["sort"], "title_asc")
        self.assertEqual(controller.calls[0]["tag"], "review")

    def test_tk_refresh_tag_filter_preserves_selected_tag_value(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        controller = _FakeController(tags=[("projekt", 2), ("review", 1)])
        app = SimpleNamespace(
            controller=controller,
            tag_display_to_value={"Alle Tags": None, "#projekt (1)": "projekt"},
            tag_filter_var=_FakeText("#projekt (1)"),
            tag_filter_combo=_FakeCombo(),
        )
        app.selected_tag_filter = lambda: module.TkTelachatApp.selected_tag_filter(app)

        module.TkTelachatApp.refresh_tag_filter(app)

        self.assertEqual(app.tag_filter_var.get(), "#projekt (2)")
        self.assertEqual(app.tag_filter_combo.values, ["Alle Tags", "#projekt (2)", "#review (1)"])


if __name__ == "__main__":
    unittest.main()
