from __future__ import annotations

import importlib
import queue
import unittest
import warnings
from types import SimpleNamespace
from unittest import mock

from telachat.client import TokenUsage
from telachat.config import ConfigError
from telachat.templates import render_prompt_template


class _FakeController:
    def __init__(
        self,
        tags: list[tuple[str, int]] | None = None,
        templates: dict[str, str] | None = None,
    ) -> None:
        self.calls: list[dict[str, object]] = []
        self.tags = tags or []
        self.templates = templates or {}

    def list_sessions(self, limit: int, **kwargs: object) -> list[object]:
        self.calls.append({"limit": limit, **kwargs})
        return []

    def list_tags(self) -> list[tuple[str, int]]:
        return self.tags

    def list_folders(self) -> list[object]:
        return []

    def stats(self) -> object:
        return _fake_stats()

    def prompt_templates(self) -> dict[str, str]:
        return self.templates

    def set_prompt_template(self, name: str, template: str) -> dict[str, str]:
        clean_name = name.strip()
        self.calls.append({"set_template": clean_name, "template": template})
        self.templates[clean_name] = template
        return self.templates

    def apply_prompt_template(
        self,
        name: str,
        text: str = "",
        *,
        values: dict[str, str] | None = None,
    ) -> str:
        self.calls.append({"apply_template": name, "text": text, "values": values or {}})
        return render_prompt_template(self.templates[name], text, values=values)


class _FakeList:
    def delete(self, *_args: object) -> None:
        return None

    def insert(self, *_args: object) -> None:
        return None

    def get_row_at_index(self, _index: int) -> object | None:
        return None


class _FakeSuggestionList:
    def __init__(self, selection: tuple[int, ...] = ()) -> None:
        self.selection = selection
        self.removed = False

    def curselection(self) -> tuple[int, ...]:
        return self.selection

    def grid_remove(self) -> None:
        self.removed = True


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
        self.model = None

    def set_selected(self, value: int) -> None:
        self.selected = value

    def set_model(self, value: object) -> None:
        self.model = value


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


class _FakeVisible:
    def __init__(self, visible: bool) -> None:
        self.visible = visible

    def get_visible(self) -> bool:
        return self.visible


class _FakeRoot:
    def __init__(self) -> None:
        self.destroyed = False
        self.after_calls: list[tuple[int, object]] = []
        self.clipboard: list[str] = []
        self.clipboard_cleared = False

    def destroy(self) -> None:
        self.destroyed = True

    def after(self, delay_ms: int, callback: object) -> None:
        self.after_calls.append((delay_ms, callback))

    def clipboard_clear(self) -> None:
        self.clipboard_cleared = True
        self.clipboard.clear()

    def clipboard_append(self, text: str) -> None:
        self.clipboard.append(text)


class _FakeButton:
    def __init__(self) -> None:
        self.state = ""
        self.sensitive = True
        self.label = ""

    def configure(self, **kwargs: object) -> None:
        if "state" in kwargs:
            self.state = str(kwargs["state"])
        if "text" in kwargs:
            self.label = str(kwargs["text"])

    def set_sensitive(self, value: bool) -> None:
        self.sensitive = value

    def set_label(self, value: str) -> None:
        self.label = value


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

    def test_tk_sidebar_quick_actions_include_visible_new_session(self) -> None:
        module = importlib.import_module("telachat.tkgui")

        self.assertEqual(module.sidebar_quick_action_labels(), ("Neu", "Regenerieren", "Check"))
        self.assertEqual(
            module.sidebar_quick_action_method_names(),
            ("new_session", "regenerate_active_session", "doctor"),
        )
        for method_name in module.sidebar_quick_action_method_names():
            self.assertTrue(hasattr(module.TkTelachatApp, method_name))
        self.assertEqual(module.SIDEBAR_FOLDER_ACTION_ROW, module.SIDEBAR_QUICK_ACTION_ROW + 2)
        self.assertEqual(module.SIDEBAR_SESSION_LIST_ROW, module.SIDEBAR_FOLDER_PROMPT_ROW + 1)

    def test_tk_refresh_template_choices_preserves_selected_template(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        combo = _FakeCombo()
        template_var = _FakeText("")
        app = SimpleNamespace(
            controller=_FakeController(templates={"summarize": "S", "brief": "B"}),
            template_combo=combo,
            template_var=template_var,
        )

        module.TkTelachatApp.refresh_template_choices(app, "brief")

        self.assertEqual(combo.cget("values"), ("summarize", "brief"))
        self.assertEqual(template_var.get(), "brief")

    def test_tk_save_input_as_template_uses_composer_text(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        controller = _FakeController(templates={"summarize": "S"})
        combo = _FakeCombo()
        template_var = _FakeText("summarize")
        statuses: list[str] = []
        app = SimpleNamespace(
            controller=controller,
            input_text=_FakeText("Neuer Prompt {input}"),
            root=object(),
            template_combo=combo,
            template_var=template_var,
            refresh_template_choices=lambda selected=None: module.TkTelachatApp.refresh_template_choices(
                app, selected
            ),
            set_status=lambda text: statuses.append(text),
            show_error=lambda text: statuses.append(f"error:{text}"),
        )

        with mock.patch.object(module.simpledialog, "askstring", return_value="brief"):
            module.TkTelachatApp.save_input_as_template(app)

        self.assertEqual(controller.templates["brief"], "Neuer Prompt {input}")
        self.assertEqual(template_var.get(), "brief")
        self.assertEqual(statuses, ["Vorlage gespeichert: brief"])

    def test_tk_preview_selected_template_opens_copyable_text_window(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        shown: list[tuple[str, str, str | None]] = []
        statuses: list[str] = []
        app = SimpleNamespace(
            controller=_FakeController(templates={"brief": "Kurz: {input}"}),
            template_var=_FakeText("brief"),
            refresh_template_choices=lambda selected=None: None,
            set_status=lambda text: statuses.append(text),
            show_text_window=lambda title, text, status_text=None: shown.append(
                (title, text, status_text)
            ),
        )

        module.TkTelachatApp.show_selected_template_preview(app)

        self.assertEqual(
            shown,
            [
                (
                    "Vorlage: brief",
                    (
                        "Name: brief\nZeichen: 13\nVariablen: {input}\n"
                        "Custom-Variablen: keine\n\nKurz: {input}"
                    ),
                    "Vorlage angezeigt: brief",
                )
            ],
        )
        self.assertEqual(statuses, [])

    def test_tk_insert_template_prompts_for_custom_variables(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        controller = _FakeController(templates={"triage": "Pruefe {topic}: {input}"})
        input_text = _FakeText("Fehler beim Login")
        statuses: list[str] = []
        app = SimpleNamespace(
            controller=controller,
            input_text=input_text,
            template_var=_FakeText("triage"),
            template_value_history={},
            refresh_template_choices=lambda selected=None: None,
            ask_template_values=lambda name, variables: {"topic": "Login"},
            set_status=lambda text: statuses.append(text),
        )

        module.TkTelachatApp.insert_template(app)

        self.assertEqual(input_text.get(), "Pruefe Login: Fehler beim Login")
        self.assertEqual(statuses, ["Vorlage eingesetzt: triage"])
        self.assertEqual(app.template_value_history, {"triage": {"topic": "Login"}})
        self.assertEqual(
            controller.calls[-1],
            {
                "apply_template": "triage",
                "text": "Fehler beim Login",
                "values": {"topic": "Login"},
            },
        )

    def test_tk_ask_template_values_skips_dialog_without_custom_variables(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        app = SimpleNamespace(root=object())

        self.assertEqual(module.TkTelachatApp.ask_template_values(app, "brief", ()), {})

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

    def test_gtk_sidebar_quick_actions_include_visible_new_session(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise

        self.assertEqual(module.sidebar_quick_action_labels(), ("Neu", "Regenerieren", "Check"))
        self.assertEqual(
            module.sidebar_quick_action_method_names(),
            ("on_new", "on_regenerate_active_session", "on_doctor"),
        )
        for method_name in module.sidebar_quick_action_method_names():
            self.assertTrue(hasattr(module.GtkTelachatApp, method_name))

    def test_gtk_refresh_template_choices_preserves_selected_template(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        dropdown = _FakeDropdown()
        app = SimpleNamespace(
            controller=_FakeController(templates={"summarize": "S", "brief": "B"}),
            template_dropdown=dropdown,
            template_names=[],
        )

        module.GtkTelachatApp.refresh_template_choices(app, "brief")

        self.assertEqual(app.template_names, ["summarize", "brief"])
        self.assertEqual(dropdown.selected, 1)

    def test_gtk_save_input_as_template_uses_composer_text(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        controller = _FakeController(templates={"summarize": "S"})
        dropdown = _FakeDropdown()
        status = _FakeText("")
        app = SimpleNamespace(
            controller=controller,
            input_prompt=lambda: "Neuer Prompt {input}",
            selected_template_name=lambda: "summarize",
            template_dropdown=dropdown,
            template_names=[],
            status=status,
            show_error=lambda text: status.set_text(f"error:{text}"),
        )
        app.refresh_template_choices = (
            lambda selected=None: module.GtkTelachatApp.refresh_template_choices(app, selected)
        )
        app._entry_dialog = lambda **kwargs: kwargs["callback"]("brief")

        module.GtkTelachatApp.on_save_input_as_template(app, object())

        self.assertEqual(controller.templates["brief"], "Neuer Prompt {input}")
        self.assertEqual(dropdown.selected, 1)
        self.assertEqual(status.get_text(), "Vorlage gespeichert: brief")

    def test_gtk_preview_selected_template_opens_copyable_text_window(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        status = _FakeText("")
        shown: list[tuple[str, str, str | None]] = []
        app = SimpleNamespace(
            controller=_FakeController(templates={"brief": "Kurz: {input}"}),
            selected_template_name=lambda: "brief",
            refresh_template_choices=lambda selected=None: None,
            status=status,
            show_text_window=lambda title, text, status_text=None: shown.append(
                (title, text, status_text)
            ),
        )

        module.GtkTelachatApp.on_preview_selected_template(app, object())

        self.assertEqual(
            shown,
            [
                (
                    "Vorlage: brief",
                    (
                        "Name: brief\nZeichen: 13\nVariablen: {input}\n"
                        "Custom-Variablen: keine\n\nKurz: {input}"
                    ),
                    "Vorlage angezeigt: brief",
                )
            ],
        )
        self.assertEqual(status.get_text(), "")

    def test_gtk_insert_template_prompts_for_custom_variables(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        controller = _FakeController(templates={"triage": "Pruefe {topic}: {input}"})
        status = _FakeText("")
        prompt = _FakeText("Fehler beim Login")
        dialogs: list[tuple[str, tuple[str, ...]]] = []

        def values_dialog(name: str, variables: tuple[str, ...], callback: object) -> None:
            dialogs.append((name, variables))
            callback({"topic": "Login"})

        app = SimpleNamespace(
            controller=controller,
            selected_template_name=lambda: "triage",
            input_prompt=lambda: prompt.get_text(),
            set_input_prompt=prompt.set_text,
            refresh_template_choices=lambda selected=None: None,
            show_template_values_dialog=values_dialog,
            template_value_history={},
            status=status,
        )
        app.insert_template_with_values = lambda name, values: (  # type: ignore[attr-defined]
            module.GtkTelachatApp.insert_template_with_values(app, name, values)
        )

        module.GtkTelachatApp.on_insert_template(app, object())

        self.assertEqual(dialogs, [("triage", ("topic",))])
        self.assertEqual(prompt.get_text(), "Pruefe Login: Fehler beim Login")
        self.assertEqual(status.get_text(), "Vorlage eingesetzt: triage")
        self.assertEqual(app.template_value_history, {"triage": {"topic": "Login"}})

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

    def test_gtk_uses_edit_prompt_for_selected_folder(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        prompts: list[str] = []
        backends: list[str] = []
        app = SimpleNamespace(
            controller=SimpleNamespace(
                folder_system_prompt_for_edit=lambda _folder_id: "Nur Prompt",
            ),
            selected_folder_id=lambda for_new=False: "folder1",
            set_system_prompt=lambda text: prompts.append(text),
            apply_selected_folder_backend=lambda folder_id: backends.append(folder_id),
        )

        module.GtkTelachatApp.apply_selected_folder_prompt(app)

        self.assertEqual(prompts, ["Nur Prompt"])
        self.assertEqual(backends, ["folder1"])

    def test_gtk_saves_folder_prompt_from_effective_prompt(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        app = SimpleNamespace(
            selected_real_folder_id=lambda: "folder1",
            system_prompt=lambda: "Prompt\n\nOrdner-Kontext:\nWissen",
            controller=SimpleNamespace(
                set_folder_system_prompt=lambda *args, **kwargs: calls.append((args, kwargs))
                or SimpleNamespace(name="Projekt")
            ),
            status=_FakeText(""),
        )

        module.GtkTelachatApp.on_save_selected_folder_prompt(app, None)

        self.assertEqual(calls[0][0], ("folder1", "Prompt\n\nOrdner-Kontext:\nWissen"))
        self.assertTrue(calls[0][1]["from_effective_prompt"])
        self.assertEqual(app.status.get_text(), "Ordner-Prompt gespeichert: Projekt")

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

    def test_tk_uses_edit_prompt_for_selected_folder(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        prompts: list[str] = []
        backends: list[str] = []
        app = SimpleNamespace(
            controller=SimpleNamespace(
                folder_system_prompt_for_edit=lambda _folder_id: "Nur Prompt",
            ),
            selected_folder_id=lambda for_new=False: "folder1",
            set_system_prompt_text=lambda text: prompts.append(text),
            apply_selected_folder_backend=lambda folder_id: backends.append(folder_id),
        )

        module.TkTelachatApp.apply_selected_folder_prompt(app)

        self.assertEqual(prompts, ["Nur Prompt"])
        self.assertEqual(backends, ["folder1"])

    def test_tk_saves_folder_prompt_from_effective_prompt(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        statuses: list[str] = []
        app = SimpleNamespace(
            selected_real_folder_id=lambda: "folder1",
            system_text=_FakeText("Prompt\n\nOrdner-Kontext:\nWissen"),
            controller=SimpleNamespace(
                set_folder_system_prompt=lambda *args, **kwargs: calls.append((args, kwargs))
                or SimpleNamespace(name="Projekt")
            ),
            set_status=lambda text: statuses.append(text),
        )

        module.TkTelachatApp.save_selected_folder_prompt(app)

        self.assertEqual(calls[0][0], ("folder1", "Prompt\n\nOrdner-Kontext:\nWissen"))
        self.assertTrue(calls[0][1]["from_effective_prompt"])
        self.assertEqual(statuses, ["Ordner-Prompt gespeichert: Projekt"])

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

    def test_tk_update_active_title_uses_plain_center_title(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        app = object.__new__(module.TkTelachatApp)
        app.active_session = SimpleNamespace(title="Projekt Alpha")
        app.session_title = _FakeText("")

        module.TkTelachatApp.update_active_title(app)

        self.assertEqual(app.session_title.get_text(), "Projekt Alpha")

    def test_tk_title_double_click_starts_rename(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        calls: list[str] = []
        app = SimpleNamespace(rename_active_session=lambda: calls.append("rename"))

        result = module.TkTelachatApp.on_title_double_click(app, object())

        self.assertEqual(result, "break")
        self.assertEqual(calls, ["rename"])

    def test_tk_sync_pane_toggle_buttons_sets_directional_labels(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        app = SimpleNamespace(
            sidebar_visible=False,
            settings_visible=True,
            sidebar_toggle_button=_FakeButton(),
            settings_toggle_button=_FakeButton(),
        )

        module.TkTelachatApp._sync_pane_toggle_buttons(app)

        self.assertEqual(app.sidebar_toggle_button.label, "▶")
        self.assertEqual(app.settings_toggle_button.label, "▶")

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

    def test_tk_shortcuts_command_shows_keyboard_help(self) -> None:
        module = importlib.import_module("telachat.tkgui")

        app = SimpleNamespace()
        app.show_shortcuts = lambda: module.TkTelachatApp.show_shortcuts(app)

        with mock.patch.object(module.messagebox, "showinfo") as showinfo:
            module.TkTelachatApp.handle_command(app, "/keys")

        showinfo.assert_called_once()
        self.assertEqual(showinfo.call_args.args[0], "Telachat Tastenkuerzel")
        self.assertIn("Shift+Enter", showinfo.call_args.args[1])
        self.assertIn("Ctrl+/", showinfo.call_args.args[1])

    def test_tk_shortcut_opens_keyboard_help(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        calls: list[str] = []
        app = SimpleNamespace(show_shortcuts=lambda: calls.append("shortcuts"))

        result = module.TkTelachatApp._show_shortcuts_from_shortcut(app, object())

        self.assertEqual(result, "break")
        self.assertEqual(calls, ["shortcuts"])

    def test_tk_complete_slash_command_uses_context_completion(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        prompt = _FakeText("/provider op")
        suggestions = _FakeSuggestionList()
        app = SimpleNamespace(
            input_text=prompt,
            command_suggestions=suggestions,
            current_command_completions=["openai "],
        )
        app.hide_command_suggestions = lambda: module.TkTelachatApp.hide_command_suggestions(app)

        result = module.TkTelachatApp.complete_slash_command(app, object())

        self.assertEqual(result, "break")
        self.assertEqual(prompt.get_text(), "/provider openai ")
        self.assertTrue(suggestions.removed)

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

    def test_tk_copy_to_clipboard_updates_clipboard_and_status(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        root = _FakeRoot()
        statuses: list[str] = []
        app = SimpleNamespace(root=root, set_status=lambda text: statuses.append(text))

        module.TkTelachatApp.copy_to_clipboard(app, "failed to load skill")

        self.assertTrue(root.clipboard_cleared)
        self.assertEqual(root.clipboard, ["failed to load skill"])
        self.assertEqual(statuses, ["In Zwischenablage kopiert."])

    def test_tk_copy_latest_assistant_response_uses_latest_answer(self) -> None:
        module = importlib.import_module("telachat.tkgui")
        copied: list[str] = []
        statuses: list[str] = []
        app = SimpleNamespace(
            messages=[
                SimpleNamespace(role="assistant", content="Erste Antwort"),
                SimpleNamespace(role="user", content="Danke"),
                SimpleNamespace(role="assistant", content="Zweite Antwort"),
            ],
            copy_to_clipboard=lambda text: copied.append(text),
            set_status=lambda text: statuses.append(text),
        )

        module.TkTelachatApp.copy_latest_assistant_response(app)

        self.assertEqual(copied, ["Zweite Antwort"])
        self.assertEqual(statuses, [])

        app.messages = [SimpleNamespace(role="user", content="Nur Frage")]
        module.TkTelachatApp.copy_latest_assistant_response(app)

        self.assertEqual(copied, ["Zweite Antwort"])
        self.assertEqual(statuses, ["Keine KI-Antwort zum Kopieren."])

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

    def test_gtk_update_active_title_uses_plain_center_title(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        app = SimpleNamespace(
            active_session=SimpleNamespace(title="Projekt Alpha"),
            title_label=_FakeText(""),
        )

        module.GtkTelachatApp.update_active_title(app)

        self.assertEqual(app.title_label.get_text(), "Projekt Alpha")

    def test_gtk_title_double_click_starts_rename(self) -> None:
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
            on_rename_active_session=lambda clicked: calls.append(clicked),
        )

        module.GtkTelachatApp.on_title_pressed(app, object(), 2, 0.0, 0.0)

        self.assertEqual(calls, [button])

    def test_gtk_sync_pane_toggle_buttons_sets_directional_labels(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        app = SimpleNamespace(
            sidebar=_FakeVisible(False),
            settings=_FakeVisible(True),
            sidebar_toggle_button=_FakeButton(),
            settings_toggle_button=_FakeButton(),
        )

        module.GtkTelachatApp.sync_pane_toggle_buttons(app)

        self.assertEqual(app.sidebar_toggle_button.label, "▶")
        self.assertEqual(app.settings_toggle_button.label, "▶")

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

    def test_gtk_shortcuts_command_shows_keyboard_help(self) -> None:
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

        app = SimpleNamespace(window=object(), status=_FakeText(""))
        app.show_shortcuts = lambda: module.GtkTelachatApp.show_shortcuts(app)

        with mock.patch.object(module.Adw, "MessageDialog", FakeMessageDialog):
            module.GtkTelachatApp.handle_command(app, "/shortcuts")

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].title, "Telachat Tastenkuerzel")
        self.assertIn("Shift+Enter", created[0].body)
        self.assertIn("Ctrl+/", created[0].body)
        self.assertEqual(created[0].responses, [("ok", "OK")])
        self.assertTrue(created[0].presented)

    def test_gtk_complete_slash_command_uses_context_completion(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        prompt = _FakeText("/theme dr")
        hidden: list[bool] = []
        app = SimpleNamespace(
            input_prompt=prompt.get_text,
            set_input_prompt=prompt.set_text,
            current_command_completions=["dracula "],
            hide_command_suggestions=lambda: hidden.append(True),
        )

        module.GtkTelachatApp.complete_slash_command(app)

        self.assertEqual(prompt.get_text(), "/theme dracula ")
        self.assertEqual(hidden, [True])

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

    def test_gtk_copy_to_clipboard_updates_clipboard_and_status(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise

        class FakeClipboard:
            def __init__(self) -> None:
                self.values: list[str] = []

            def set(self, text: str) -> None:
                self.values.append(text)

        class FakeDisplay:
            def __init__(self, clipboard: FakeClipboard) -> None:
                self.clipboard = clipboard

            def get_clipboard(self) -> FakeClipboard:
                return self.clipboard

        clipboard = FakeClipboard()
        app = SimpleNamespace(status=_FakeText(""))

        with mock.patch.object(
            module.Gdk.Display,
            "get_default",
            return_value=FakeDisplay(clipboard),
        ):
            module.GtkTelachatApp.copy_to_clipboard(app, "failed to load skill")

        self.assertEqual(clipboard.values, ["failed to load skill"])
        self.assertEqual(app.status.get_text(), "In Zwischenablage kopiert.")

    def test_gtk_copy_latest_assistant_response_uses_latest_answer(self) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                module = importlib.import_module("telachat.gtkgui")
            except ModuleNotFoundError as exc:
                if exc.name == "gi":
                    self.skipTest("PyGObject is not installed in this environment")
                raise
        copied: list[str] = []
        app = SimpleNamespace(
            messages=[
                SimpleNamespace(role="assistant", content="Erste Antwort"),
                SimpleNamespace(role="user", content="Danke"),
                SimpleNamespace(role="assistant", content="Zweite Antwort"),
            ],
            copy_to_clipboard=lambda text: copied.append(text),
            status=_FakeText(""),
        )

        module.GtkTelachatApp.on_copy_latest_assistant_response(app, None)

        self.assertEqual(copied, ["Zweite Antwort"])
        self.assertEqual(app.status.get_text(), "")

        app.messages = [SimpleNamespace(role="user", content="Nur Frage")]
        module.GtkTelachatApp.on_copy_latest_assistant_response(app, None)

        self.assertEqual(copied, ["Zweite Antwort"])
        self.assertEqual(app.status.get_text(), "Keine KI-Antwort zum Kopieren.")

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
