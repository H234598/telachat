from __future__ import annotations

import importlib
import queue
import unittest
import warnings
from types import SimpleNamespace
from unittest import mock

from telachat.client import TokenUsage
from telachat.config import ConfigError


class _FakeController:
    def __init__(self, tags: list[tuple[str, int]] | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.tags = tags or []

    def list_sessions(self, limit: int, **kwargs: object) -> list[object]:
        self.calls.append({"limit": limit, **kwargs})
        return []

    def list_tags(self) -> list[tuple[str, int]]:
        return self.tags

    def list_folders(self) -> list[object]:
        return []

    def stats(self) -> object:
        return _fake_stats()


class _FakeList:
    def delete(self, *_args: object) -> None:
        return None

    def insert(self, *_args: object) -> None:
        return None

    def get_row_at_index(self, _index: int) -> object | None:
        return None


class _FakeText:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self, *_args: object) -> str:
        return self.value

    def get_text(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value

    def set_text(self, value: str) -> None:
        self.value = value

    def insert(self, _index: str, value: str) -> None:
        self.value = value

    def delete(self, *_args: object) -> None:
        self.value = ""

    def configure(self, **kwargs: object) -> None:
        if "text" in kwargs:
            self.value = str(kwargs["text"])


class _FakeCombo:
    def __init__(self) -> None:
        self.values: list[str] = []

    def configure(self, **kwargs: object) -> None:
        self.values = list(kwargs.get("values", ()))

    def cget(self, key: str) -> object:
        if key == "values":
            return tuple(self.values)
        raise KeyError(key)


class _FakeBoolVar:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value

    def set(self, value: bool) -> None:
        self.value = value


class _FakeDropdown:
    def __init__(self) -> None:
        self.selected = -1

    def set_selected(self, value: int) -> None:
        self.selected = value


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


class _FakeWindow:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakeRoot:
    def __init__(self) -> None:
        self.destroyed = False
        self.after_calls: list[tuple[int, object]] = []

    def destroy(self) -> None:
        self.destroyed = True

    def after(self, delay_ms: int, callback: object) -> None:
        self.after_calls.append((delay_ms, callback))


class _FakeButton:
    def __init__(self) -> None:
        self.state = ""
        self.sensitive = True

    def configure(self, **kwargs: object) -> None:
        if "state" in kwargs:
            self.state = str(kwargs["state"])

    def set_sensitive(self, value: bool) -> None:
        self.sensitive = value


class _FakeCheckButton:
    def __init__(self, active: bool) -> None:
        self.active = active

    def get_active(self) -> bool:
        return self.active

    def set_active(self, value: bool) -> None:
        self.active = value


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
            session_rows=[],
            _insert_grouped_session_rows=lambda: None,
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

    def test_gtk_applies_folder_backend_defaults(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        app = SimpleNamespace(
            controller=SimpleNamespace(folder_backend=lambda _folder_id: ("work", "folder-model")),
            profile_names=["work"],
            profile_dropdown=_FakeDropdown(),
            model_names=["folder-model"],
            model_dropdown=_FakeDropdown(),
            refresh_models=lambda: None,
        )

        module.GtkTelachatApp.apply_selected_folder_backend(app, "folder1")

        self.assertEqual(app.profile_dropdown.selected, 0)
        self.assertEqual(app.model_dropdown.selected, 0)

    def test_gtk_ignores_folder_model_when_profile_is_unknown(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        app = SimpleNamespace(
            controller=SimpleNamespace(folder_backend=lambda _folder_id: ("missing", "folder-model")),
            profile_names=["work"],
            profile_dropdown=_FakeDropdown(),
            model_names=["base-model"],
            model_dropdown=_FakeDropdown(),
            refresh_models=lambda: None,
        )

        module.GtkTelachatApp.apply_selected_folder_backend(app, "folder1")

        self.assertEqual(app.profile_dropdown.selected, -1)
        self.assertEqual(app.model_dropdown.selected, -1)
        self.assertEqual(app.model_names, ["base-model"])

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

    def test_tk_applies_folder_backend_defaults(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        profile = SimpleNamespace(
            model="base-model",
            models=["base-model"],
            temperature=0.7,
            max_tokens=2048,
        )
        app = SimpleNamespace(
            controller=SimpleNamespace(
                folder_backend=lambda _folder_id: ("work", "folder-model"),
                profiles=lambda: {"work": profile},
            ),
            profile_display_to_name={"Work": "work"},
            profile_var=_FakeText(""),
            model_combo=_FakeCombo(),
            model_var=_FakeText(""),
            temperature_var=_FakeText(""),
            max_tokens_var=_FakeText(""),
        )
        app.refresh_models = lambda: module.TkTelachatApp.refresh_models(app)
        app.selected_profile = lambda: module.TkTelachatApp.selected_profile(app)
        app.refresh_generation_defaults = lambda: module.TkTelachatApp.refresh_generation_defaults(app)

        module.TkTelachatApp.apply_selected_folder_backend(app, "folder1")

        self.assertEqual(app.profile_var.get(), "Work")
        self.assertEqual(app.model_var.get(), "folder-model")
        self.assertEqual(app.model_combo.values, ["folder-model", "base-model"])

    def test_tk_ignores_folder_model_when_profile_is_unknown(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        app = SimpleNamespace(
            controller=SimpleNamespace(folder_backend=lambda _folder_id: ("missing", "folder-model")),
            profile_display_to_name={"Work": "work"},
            profile_var=_FakeText(""),
            model_combo=_FakeCombo(),
            model_var=_FakeText(""),
        )
        app.model_combo.configure(values=["base-model"])
        app.refresh_models = lambda: module.TkTelachatApp.refresh_models(app)

        module.TkTelachatApp.apply_selected_folder_backend(app, "folder1")

        self.assertEqual(app.profile_var.get(), "")
        self.assertEqual(app.model_var.get(), "")
        self.assertEqual(app.model_combo.values, ["base-model"])

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

    def test_tk_response_status_reports_usage_when_available(self) -> None:
        module = importlib.import_module("telachat.tkgui")

        status = module.TkTelachatApp.response_status(
            SimpleNamespace(),
            SimpleNamespace(
                elapsed_seconds=1.24,
                usage=TokenUsage(input_tokens=13, output_tokens=18, total_tokens=31),
            ),
        )

        self.assertEqual(status, "Antwort in 1.2s | Tokens: 13 in/18 out, 31 total")

    def test_tk_cancelled_request_ignores_late_result(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        app = object.__new__(module.TkTelachatApp)
        app.active_operation_id = 4
        app.cancelled_operation_ids = set()
        app.operation_prompt_drafts = {4: "Bitte nochmal pruefen"}
        app.operation_counter = 4
        app.active_session = SimpleNamespace(id="old")
        app.messages = []
        app.events = queue.Queue()
        app.root = _FakeRoot()
        app.status = _FakeText("")
        app.input_text = _FakeText("")
        app.send_button = _FakeButton()
        app.cancel_button = _FakeButton()
        app.update_active_title = mock.Mock()
        app.refresh_sessions = mock.Mock()
        app.render_messages = mock.Mock()

        module.TkTelachatApp.cancel_active_request(app)
        app.events.put(
            (
                "sent",
                (
                    4,
                    SimpleNamespace(
                        session=SimpleNamespace(id="new"),
                        messages=[SimpleNamespace(content="late")],
                    ),
                ),
            )
        )
        module.TkTelachatApp._poll_events(app)

        self.assertIsNone(app.active_operation_id)
        self.assertEqual(app.active_session.id, "old")
        self.assertEqual(app.messages, [])
        self.assertEqual(app.input_text.get_text(), "Bitte nochmal pruefen")
        self.assertEqual(app.operation_prompt_drafts, {})
        self.assertEqual(app.status.get_text(), "Abgebrochen; Ergebnis wird ignoriert")
        self.assertEqual(app.send_button.state, "normal")
        self.assertEqual(app.cancel_button.state, "disabled")
        app.update_active_title.assert_not_called()
        app.refresh_sessions.assert_not_called()
        app.render_messages.assert_not_called()
        self.assertEqual(app.root.after_calls[0][0], 100)

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

    def test_tk_context_command_shows_content_free_estimate(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        app = SimpleNamespace(
            controller=SimpleNamespace(config=SimpleNamespace(max_history_messages=1)),
            messages=[
                SimpleNamespace(content="Geheimer Projektplan"),
                SimpleNamespace(content="Antwort"),
            ],
            system_text=_FakeText("System"),
            statuses=[],
        )
        app.set_status = lambda text: app.statuses.append(text)

        with mock.patch.object(module.messagebox, "showinfo") as showinfo:
            module.TkTelachatApp.handle_command(app, "/context")

        showinfo.assert_called_once()
        self.assertEqual(showinfo.call_args.args[0], "Telachat Kontext")
        self.assertIn("1 im naechsten Request", showinfo.call_args.args[1])
        self.assertNotIn("Geheimer Projektplan", showinfo.call_args.args[1])
        self.assertEqual(app.statuses[-1], "Kontext ca. 4 Tokens | 1/2 Nachrichten")

    def test_tk_doctor_command_starts_existing_check(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        calls: list[str] = []
        app = SimpleNamespace(doctor=lambda: calls.append("doctor"))

        module.TkTelachatApp.handle_command(app, "/doctor")

        self.assertEqual(calls, ["doctor"])

    def test_tk_header_validation_toggle_updates_status(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        calls: list[bool] = []
        controller = SimpleNamespace(
            config=SimpleNamespace(validate_profile_headers=True),
            set_header_validation=lambda enabled: calls.append(enabled) or enabled,
        )
        statuses: list[str] = []
        app = SimpleNamespace(
            controller=controller,
            header_validation_var=_FakeBoolVar(False),
            set_status=lambda text: statuses.append(text),
        )

        module.TkTelachatApp.on_header_validation_changed(app)

        self.assertEqual(calls, [False])
        self.assertFalse(app.header_validation_var.get())
        self.assertEqual(statuses, ["Header-Pruefung: aus"])

    def test_tk_header_validation_toggle_rolls_back_on_error(self) -> None:
        module = importlib.import_module("telachat.tkgui")

        def fail(_enabled: bool) -> bool:
            raise ConfigError("Header kaputt")

        app = SimpleNamespace(
            controller=SimpleNamespace(
                config=SimpleNamespace(validate_profile_headers=True),
                set_header_validation=fail,
            ),
            header_validation_var=_FakeBoolVar(False),
            statuses=[],
        )
        app.set_status = lambda text: app.statuses.append(text)

        module.TkTelachatApp.on_header_validation_changed(app)

        self.assertTrue(app.header_validation_var.get())
        self.assertEqual(app.statuses, ["Header kaputt"])

    def test_tk_models_command_lists_configured_models(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        combo = _FakeCombo()
        combo.configure(values=["base-model", "backup-model"])
        app = SimpleNamespace(model_combo=combo)

        with mock.patch.object(module.messagebox, "showinfo") as showinfo:
            module.TkTelachatApp.handle_command(app, "/models")

        showinfo.assert_called_once()
        self.assertEqual(showinfo.call_args.args[0], "Telachat Modelle")
        self.assertEqual(showinfo.call_args.args[1], "base-model\nbackup-model")

    def test_tk_models_live_command_starts_existing_check(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        calls: list[str] = []
        app = SimpleNamespace(doctor=lambda: calls.append("doctor"))

        module.TkTelachatApp.handle_command(app, "/models live")

        self.assertEqual(calls, ["doctor"])

    def test_tk_doctor_result_refreshes_model_choices(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        events: queue.Queue[object] = queue.Queue()
        events.put(("doctor", (7, ["live-a", "live-b"])))
        refreshed: list[list[str]] = []
        finished: list[tuple[int, str]] = []
        app = SimpleNamespace(
            events=events,
            root=_FakeRoot(),
            _poll_events=lambda: None,
            operation_result_current=lambda operation_id: operation_id == 7,
            update_model_choices_from_live=lambda models: refreshed.append(list(models)),
            finish_operation=lambda operation_id, status: finished.append((operation_id, status)),
        )

        module.TkTelachatApp._poll_events(app)

        self.assertEqual(refreshed, [["live-a", "live-b"]])
        self.assertEqual(finished, [(7, "OK: live-a, live-b")])
        self.assertEqual(app.root.after_calls[0][0], 100)

    def test_tk_error_event_uses_copyable_error_dialog(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        events: queue.Queue[object] = queue.Queue()
        events.put(("error", (9, RuntimeError("failed to load skill\nexceeds maximum"))))
        finished: list[tuple[int, str]] = []
        shown_errors: list[str] = []
        app = SimpleNamespace(
            events=events,
            root=_FakeRoot(),
            _poll_events=lambda: None,
            operation_result_current=lambda operation_id: operation_id == 9,
            finish_operation=lambda operation_id, status: finished.append(
                (operation_id, status)
            ),
            show_error=lambda text: shown_errors.append(text),
        )

        with mock.patch.object(module.messagebox, "showerror") as showerror:
            module.TkTelachatApp._poll_events(app)

        self.assertEqual(finished, [(9, "Fehler")])
        self.assertEqual(shown_errors, ["failed to load skill\nexceeds maximum"])
        showerror.assert_not_called()
        self.assertEqual(app.root.after_calls[0][0], 100)

    def test_tk_exit_alias_closes_window(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        root = _FakeRoot()
        app = SimpleNamespace(root=root)

        module.TkTelachatApp.handle_command(app, "/q")

        self.assertTrue(root.destroyed)

    def test_tk_regenerate_alias_uses_shared_command_catalog(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        calls: list[str] = []
        app = SimpleNamespace(regenerate_active_session=lambda: calls.append("regen"))

        module.TkTelachatApp.handle_command(app, "/regenerate")

        self.assertEqual(calls, ["regen"])

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

    def test_gtk_response_status_reports_usage_when_available(self) -> None:
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
            SimpleNamespace(
                elapsed_seconds=2.05,
                usage=TokenUsage(input_tokens=21, output_tokens=8, total_tokens=29),
            ),
        )

        self.assertEqual(status, "Antwort in 2.0s | Tokens: 21 in/8 out, 29 total")

    def test_gtk_cancelled_request_ignores_late_result(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        app = SimpleNamespace(
            active_operation_id=2,
            cancelled_operation_ids=set(),
            operation_prompt_drafts={2: "Bitte nochmal pruefen"},
            operation_counter=2,
            active_session=SimpleNamespace(id="old"),
            messages=[],
            status=_FakeText(""),
            send_button=_FakeButton(),
            cancel_button=_FakeButton(),
            update_active_title=mock.Mock(),
            refresh_sessions=mock.Mock(),
            render_messages=mock.Mock(),
        )
        input_text = _FakeText("")
        app.input_prompt = lambda: input_text.get_text()
        app.set_input_prompt = lambda text: input_text.set_text(text)
        app.set_busy = lambda busy, text: module.GtkTelachatApp.set_busy(app, busy, text)
        app.operation_result_current = lambda operation_id: module.GtkTelachatApp.operation_result_current(
            app, operation_id
        )
        app.restore_operation_prompt = lambda text: module.GtkTelachatApp.restore_operation_prompt(
            app, text
        )
        app.finish_operation = lambda operation_id, text: module.GtkTelachatApp.finish_operation(
            app, operation_id, text
        )
        app.response_status = lambda payload: module.GtkTelachatApp.response_status(app, payload)

        module.GtkTelachatApp.cancel_active_request(app, None)
        module.GtkTelachatApp._send_done(
            app,
            2,
            SimpleNamespace(
                session=SimpleNamespace(id="new"),
                messages=[SimpleNamespace(content="late")],
            ),
        )

        self.assertIsNone(app.active_operation_id)
        self.assertEqual(app.active_session.id, "old")
        self.assertEqual(app.messages, [])
        self.assertEqual(input_text.get_text(), "Bitte nochmal pruefen")
        self.assertEqual(app.operation_prompt_drafts, {})
        self.assertEqual(app.status.get_text(), "Abgebrochen; Ergebnis wird ignoriert")
        self.assertTrue(app.send_button.sensitive)
        self.assertFalse(app.cancel_button.sensitive)
        app.update_active_title.assert_not_called()
        app.refresh_sessions.assert_not_called()
        app.render_messages.assert_not_called()

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

    def test_gtk_context_command_shows_content_free_estimate(self) -> None:
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
            controller=SimpleNamespace(config=SimpleNamespace(max_history_messages=1)),
            messages=[
                SimpleNamespace(content="Geheimer Projektplan"),
                SimpleNamespace(content="Antwort"),
            ],
            system_prompt=lambda: "System",
            window=object(),
            status=_FakeText(""),
        )

        with mock.patch.object(module.Adw, "MessageDialog", FakeMessageDialog):
            module.GtkTelachatApp.handle_command(app, "/context")

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].title, "Telachat Kontext")
        self.assertIn("1 im naechsten Request", created[0].body)
        self.assertNotIn("Geheimer Projektplan", created[0].body)
        self.assertEqual(created[0].responses, [("ok", "OK")])
        self.assertTrue(created[0].presented)
        self.assertEqual(app.status.get_text(), "Kontext ca. 4 Tokens | 1/2 Nachrichten")

    def test_gtk_doctor_command_starts_existing_check(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        calls: list[str] = []
        app = SimpleNamespace(doctor=lambda: calls.append("doctor"))

        module.GtkTelachatApp.handle_command(app, "/doctor")

        self.assertEqual(calls, ["doctor"])

    def test_gtk_header_validation_toggle_updates_status(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        calls: list[bool] = []
        button = _FakeCheckButton(False)
        app = SimpleNamespace(
            controller=SimpleNamespace(
                config=SimpleNamespace(validate_profile_headers=True),
                set_header_validation=lambda enabled: calls.append(enabled) or enabled,
            ),
            header_validation_check=button,
            status=_FakeText(""),
        )
        app._sync_header_validation_check = (
            lambda enabled: module.GtkTelachatApp._sync_header_validation_check(app, enabled)
        )

        module.GtkTelachatApp.on_header_validation_toggled(app, button)

        self.assertEqual(calls, [False])
        self.assertFalse(button.get_active())
        self.assertFalse(getattr(app, "_syncing_header_validation", False))
        self.assertEqual(app.status.get_text(), "Header-Pruefung: aus")

    def test_gtk_header_validation_toggle_rolls_back_on_error(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise

        def fail(_enabled: bool) -> bool:
            raise ConfigError("Header kaputt")

        button = _FakeCheckButton(False)
        app = SimpleNamespace(
            controller=SimpleNamespace(
                config=SimpleNamespace(validate_profile_headers=True),
                set_header_validation=fail,
            ),
            header_validation_check=button,
            status=_FakeText(""),
        )
        app._sync_header_validation_check = (
            lambda enabled: module.GtkTelachatApp._sync_header_validation_check(app, enabled)
        )

        module.GtkTelachatApp.on_header_validation_toggled(app, button)

        self.assertTrue(button.get_active())
        self.assertFalse(getattr(app, "_syncing_header_validation", False))
        self.assertEqual(app.status.get_text(), "Header kaputt")

    def test_gtk_models_command_lists_configured_models(self) -> None:
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
            model_names=["base-model", "backup-model"],
            window=object(),
        )

        with mock.patch.object(module.Adw, "MessageDialog", FakeMessageDialog):
            module.GtkTelachatApp.handle_command(app, "/models")

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].title, "Telachat Modelle")
        self.assertEqual(created[0].body, "base-model\nbackup-model")
        self.assertEqual(created[0].responses, [("ok", "OK")])
        self.assertTrue(created[0].presented)

    def test_gtk_models_live_command_starts_existing_check(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        calls: list[str] = []
        app = SimpleNamespace(doctor=lambda: calls.append("doctor"))

        module.GtkTelachatApp.handle_command(app, "/models live")

        self.assertEqual(calls, ["doctor"])

    def test_gtk_doctor_done_refreshes_model_choices(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        refreshed: list[list[str]] = []
        finished: list[tuple[int, str]] = []
        app = SimpleNamespace(
            operation_result_current=lambda operation_id: operation_id == 11,
            update_model_choices_from_live=lambda models: refreshed.append(list(models)),
            finish_operation=lambda operation_id, status: finished.append((operation_id, status)),
        )

        result = module.GtkTelachatApp._doctor_done(app, 11, ["live-a", "live-b"])

        self.assertEqual(result, module.GLib.SOURCE_REMOVE)
        self.assertEqual(refreshed, [["live-a", "live-b"]])
        self.assertEqual(finished, [(11, "OK: live-a, live-b")])

    def test_gtk_error_uses_copyable_error_window(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        finished: list[tuple[int, str]] = []
        shown_errors: list[str] = []
        app = SimpleNamespace(
            operation_result_current=lambda operation_id: operation_id == 12,
            finish_operation=lambda operation_id, status: finished.append(
                (operation_id, status)
            ),
            show_error=lambda text: shown_errors.append(text),
        )

        result = module.GtkTelachatApp._error(
            app,
            12,
            RuntimeError("failed to load skill\nexceeds maximum"),
        )

        self.assertEqual(result, module.GLib.SOURCE_REMOVE)
        self.assertEqual(finished, [(12, "Fehler")])
        self.assertEqual(shown_errors, ["failed to load skill\nexceeds maximum"])

    def test_gtk_exit_alias_closes_window(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        window = _FakeWindow()
        app = SimpleNamespace(window=window)

        module.GtkTelachatApp.handle_command(app, "/quit")

        self.assertTrue(window.closed)

    def test_gtk_regenerate_alias_uses_shared_command_catalog(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        calls: list[object] = []
        button = object()
        app = SimpleNamespace(
            send_button=button,
            on_regenerate_active_session=lambda clicked: calls.append(clicked),
        )

        module.GtkTelachatApp.handle_command(app, "/regenerate")

        self.assertEqual(calls, [button])


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
