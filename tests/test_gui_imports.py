from __future__ import annotations

import importlib
import unittest
import warnings
from types import SimpleNamespace
from unittest import mock


class _FakeController:
    def __init__(self, tags: list[tuple[str, int]] | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.tags = tags or []

    def list_sessions(self, limit: int, **kwargs: object) -> list[object]:
        self.calls.append({"limit": limit, **kwargs})
        return []

    def list_tags(self) -> list[tuple[str, int]]:
        return self.tags

    def stats(self) -> object:
        return _fake_stats()


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

    def set_text(self, value: str) -> None:
        self.value = value


class _FakeCombo:
    def __init__(self) -> None:
        self.values: list[str] = []

    def configure(self, **kwargs: object) -> None:
        self.values = list(kwargs.get("values", ()))


class _FakeSpin:
    def __init__(self, value: float) -> None:
        self.value = value

    def get_value(self) -> float:
        return self.value

    def get_value_as_int(self) -> int:
        return int(self.value)


class _FakeDialog:
    def __init__(self, title: str, body: str) -> None:
        self.title = title
        self.body = body
        self.responses: list[tuple[str, str]] = []
        self.presented = False

    def add_response(self, response_id: str, label: str) -> None:
        self.responses.append((response_id, label))

    def present(self) -> None:
        self.presented = True


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

    def test_tk_generation_inputs_normalize_to_supported_ranges(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        profile = SimpleNamespace(temperature=0.7, max_tokens=2048)
        app = SimpleNamespace(
            controller=SimpleNamespace(profiles=lambda: {"test": profile}),
            selected_profile=lambda: "test",
            temperature_var=_FakeText("2,7"),
            max_tokens_var=_FakeText("0"),
        )

        self.assertEqual(module.TkTelachatApp.selected_temperature(app), 2.0)
        self.assertEqual(module.TkTelachatApp.selected_max_tokens(app), 1)
        self.assertEqual(app.temperature_var.get(), "2")
        self.assertEqual(app.max_tokens_var.get(), "1")

    def test_gtk_generation_inputs_read_spin_values(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        app = SimpleNamespace(
            temperature_spin=_FakeSpin(0.85),
            max_tokens_spin=_FakeSpin(2048),
        )

        self.assertEqual(module.GtkTelachatApp.selected_temperature(app), 0.85)
        self.assertEqual(module.GtkTelachatApp.selected_max_tokens(app), 2048)

    def test_tk_response_status_reports_elapsed_time(self) -> None:
        module = importlib.import_module("telachat.tkgui")

        status = module.TkTelachatApp.response_status(
            SimpleNamespace(),
            SimpleNamespace(elapsed_seconds=1.24),
        )

        self.assertEqual(status, "Antwort in 1.2s")

    def test_tk_stats_command_shows_summary_without_database_path(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        app = SimpleNamespace(controller=_FakeController(), statuses=[])
        app.set_status = lambda text: app.statuses.append(text)

        with mock.patch.object(module.messagebox, "showinfo") as showinfo:
            module.TkTelachatApp.handle_command(app, "/stats")

        showinfo.assert_called_once()
        self.assertEqual(showinfo.call_args.args[0], "Telachat Statistik")
        self.assertIn("Sessions: 2 gesamt", showinfo.call_args.args[1])
        self.assertNotIn("SQLite:", showinfo.call_args.args[1])
        self.assertEqual(app.statuses[-1], "Sessions 2 | Nachrichten 4 | Ordner 1 | Tags 1")

    def test_gtk_response_status_reports_elapsed_time(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise

        status = module.GtkTelachatApp.response_status(
            SimpleNamespace(),
            SimpleNamespace(elapsed_seconds=2.05),
        )

        self.assertEqual(status, "Antwort in 2.0s")

    def test_gtk_stats_command_shows_summary_without_database_path(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        created: list[_FakeDialog] = []

        class FakeMessageDialog:
            @staticmethod
            def new(_parent: object, title: str, body: str) -> _FakeDialog:
                dialog = _FakeDialog(title, body)
                created.append(dialog)
                return dialog

        app = SimpleNamespace(
            controller=_FakeController(),
            window=object(),
            status=_FakeText(""),
        )

        with mock.patch.object(module.Adw, "MessageDialog", FakeMessageDialog):
            module.GtkTelachatApp.handle_command(app, "/stats")

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].title, "Telachat Statistik")
        self.assertIn("Sessions: 2 gesamt", created[0].body)
        self.assertNotIn("SQLite:", created[0].body)
        self.assertEqual(created[0].responses, [("ok", "OK")])
        self.assertTrue(created[0].presented)
        self.assertEqual(app.status.get_text(), "Sessions 2 | Nachrichten 4 | Ordner 1 | Tags 1")


def _fake_stats() -> object:
    return SimpleNamespace(
        database_path="/tmp/history.sqlite3",
        sessions_total=2,
        sessions_active=1,
        sessions_archived=1,
        sessions_pinned=1,
        sessions_unfiled=1,
        folders_total=1,
        folders_with_system_prompt=0,
        tags_total=1,
        tag_links_total=2,
        tagged_sessions=2,
        messages_total=4,
        message_roles=(("assistant", 2), ("user", 2)),
        session_profiles=(("tki", 2),),
        session_models=(("", 2),),
    )


if __name__ == "__main__":
    unittest.main()
