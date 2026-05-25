from __future__ import annotations

import argparse
import os
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from .commands import (
    canonical_slash_command,
    estimate_context,
    format_context_lines,
    format_context_summary,
    format_message_matches,
    format_stats_lines,
    format_stats_summary,
    slash_command_help,
    slash_command_suggestions,
)
from .config import redact_secret
from .controller import TelachatController
from .model_choices import merge_model_choices
from .store import Message, Session
from .themes import theme_by_name


class GtkTelachatApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id="de.teladi.Telachat",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        self.controller: TelachatController | None = None
        self.active_session: Session | None = None
        self.messages: list[Message] = []
        self.sessions: list[Session] = []
        self.operation_counter = 0
        self.active_operation_id: int | None = None
        self.cancelled_operation_ids: set[int] = set()
        self.folder_display_to_id: dict[str, str | None] = {}
        self.tag_filter_values: dict[str, str | None] = {"Alle Tags": None}
        self.sort_keys = {
            "Neueste zuerst": "updated_desc",
            "Aelteste zuerst": "updated_asc",
            "Titel A-Z": "title_asc",
            "Titel Z-A": "title_desc",
            "Provider": "profile_asc",
        }
        self.archive_filter_keys = {
            "Aktiv": "active",
            "Archiv": "archived",
            "Alle": "all",
        }
        self.connect("activate", self.on_activate)

    def on_activate(self, _app: Adw.Application) -> None:
        self.controller = TelachatController()
        self.theme = self.controller.theme()
        self._install_css()
        self.window = Adw.ApplicationWindow(application=self)
        self.window.add_css_class("telachat-window")
        self.window.set_title("Telachat GTK")
        self.window.set_default_size(1120, 720)
        self.window.connect("close-request", self.on_close)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Telachat GTK"))
        sidebar_button = Gtk.Button(label="☰")
        sidebar_button.connect("clicked", self.on_toggle_sidebar)
        header.pack_start(sidebar_button)
        system_button = Gtk.Button(label="System")
        system_button.connect("clicked", self.on_toggle_settings)
        header.pack_end(system_button)
        toolbar.add_top_bar(header)

        self.outer_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.outer_paned.set_wide_handle(True)
        self.outer_paned.set_resize_start_child(False)
        self.outer_paned.set_resize_end_child(True)
        self.outer_paned.set_shrink_start_child(False)
        self.outer_paned.set_shrink_end_child(False)

        self.inner_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.inner_paned.set_wide_handle(True)
        self.inner_paned.set_resize_start_child(True)
        self.inner_paned.set_resize_end_child(False)
        self.inner_paned.set_shrink_start_child(False)
        self.inner_paned.set_shrink_end_child(False)

        toolbar.set_content(self.outer_paned)
        self.window.set_content(toolbar)

        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.sidebar.add_css_class("telachat-panel")
        self.sidebar.set_size_request(280, -1)
        self.sidebar.set_margin_top(14)
        self.sidebar.set_margin_bottom(14)
        self.sidebar.set_margin_start(14)
        self.sidebar.set_margin_end(14)
        self.outer_paned.set_start_child(self.sidebar)
        self.outer_paned.set_end_child(self.inner_paned)

        self.status = Gtk.Label(label="Bereit", xalign=0)
        self.status.add_css_class("dim-label")
        self.sidebar.append(self.status)

        self.profile_names = []
        profile_labels = []
        for name, profile in sorted(self.controller.profiles().items()):
            self.profile_names.append(name)
            profile_labels.append(profile.display_name)
        self.sidebar.append(Gtk.Label(label="Provider", xalign=0))
        self.profile_dropdown = Gtk.DropDown.new(Gtk.StringList.new(profile_labels), None)
        try:
            selected = self.profile_names.index(self.controller.default_profile_name())
        except ValueError:
            selected = 0
        self.profile_dropdown.set_selected(selected)
        self.profile_dropdown.connect("notify::selected", self.on_profile_changed)
        self.sidebar.append(self.profile_dropdown)

        self.sidebar.append(Gtk.Label(label="Modell", xalign=0))
        self.model_names: list[str] = []
        self.model_dropdown = Gtk.DropDown()
        self.sidebar.append(self.model_dropdown)
        self.refresh_models()

        self.sidebar.append(Gtk.Label(label="Ordner", xalign=0))
        self.folder_dropdown = Gtk.DropDown()
        self.folder_dropdown.connect("notify::selected", self.on_filter_changed)
        self.sidebar.append(self.folder_dropdown)

        self.sidebar.append(Gtk.Label(label="Ansicht", xalign=0))
        self.archive_filter_dropdown = Gtk.DropDown.new(
            Gtk.StringList.new(list(self.archive_filter_keys)),
            None,
        )
        self.archive_filter_dropdown.set_selected(0)
        self.archive_filter_dropdown.connect("notify::selected", self.on_filter_changed)
        self.sidebar.append(self.archive_filter_dropdown)

        self.sidebar.append(Gtk.Label(label="Tag", xalign=0))
        self.tag_filter_dropdown = Gtk.DropDown.new(
            Gtk.StringList.new(list(self.tag_filter_values)),
            None,
        )
        self.tag_filter_dropdown.set_selected(0)
        self.tag_filter_dropdown.connect("notify::selected", self.on_filter_changed)
        self.sidebar.append(self.tag_filter_dropdown)

        self.sidebar.append(Gtk.Label(label="Sortierung", xalign=0))
        self.sort_dropdown = Gtk.DropDown.new(Gtk.StringList.new(list(self.sort_keys)), None)
        self.sort_dropdown.set_selected(0)
        self.sort_dropdown.connect("notify::selected", self.on_filter_changed)
        self.sidebar.append(self.sort_dropdown)

        self.sidebar.append(Gtk.Label(label="Suche", xalign=0))
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.connect("search-changed", self.on_filter_changed)
        self.sidebar.append(self.search_entry)

        self.template_names = list(self.controller.prompt_templates())
        self.sidebar.append(Gtk.Label(label="Vorlage", xalign=0))
        self.template_dropdown = Gtk.DropDown.new(Gtk.StringList.new(self.template_names), None)
        self.sidebar.append(self.template_dropdown)
        template_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.sidebar.append(template_row)
        insert_template_button = Gtk.Button(label="Einsetzen")
        insert_template_button.connect("clicked", self.on_insert_template)
        template_row.append(insert_template_button)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.sidebar.append(row)
        new_button = Gtk.Button(label="Neu")
        new_button.connect("clicked", self.on_new)
        row.append(new_button)
        check_button = Gtk.Button(label="Check")
        check_button.connect("clicked", self.on_doctor)
        row.append(check_button)

        folder_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.sidebar.append(folder_row)
        create_folder_button = Gtk.Button(label="Ordner +")
        create_folder_button.connect("clicked", self.on_create_folder)
        folder_row.append(create_folder_button)
        move_button = Gtk.Button(label="Ablegen")
        move_button.connect("clicked", self.on_move_active_to_folder)
        folder_row.append(move_button)

        folder_manage_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.sidebar.append(folder_manage_row)
        rename_folder_button = Gtk.Button(label="Ordner um")
        rename_folder_button.connect("clicked", self.on_rename_selected_folder)
        folder_manage_row.append(rename_folder_button)
        delete_folder_button = Gtk.Button(label="Ordner -")
        delete_folder_button.connect("clicked", self.on_delete_selected_folder)
        folder_manage_row.append(delete_folder_button)

        folder_prompt_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.sidebar.append(folder_prompt_row)
        folder_prompt_button = Gtk.Button(label="Ordner-Prompt")
        folder_prompt_button.connect("clicked", self.on_save_selected_folder_prompt)
        folder_prompt_row.append(folder_prompt_button)

        self.session_list = Gtk.ListBox()
        self.session_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.session_list.connect("row-selected", self.on_session_selected)
        sc_sessions = Gtk.ScrolledWindow()
        sc_sessions.set_child(self.session_list)
        sc_sessions.set_vexpand(True)
        self.sidebar.append(sc_sessions)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main.add_css_class("telachat-main")
        main.set_margin_top(14)
        main.set_margin_bottom(14)
        main.set_margin_start(10)
        main.set_margin_end(10)
        main.set_hexpand(True)
        self.inner_paned.set_start_child(main)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        main.append(top)
        self.title_label = Gtk.Label(label="Neue Unterhaltung", xalign=0)
        self.title_label.add_css_class("title-2")
        self.title_label.set_hexpand(True)
        top.append(self.title_label)
        self.pin_button = Gtk.Button(label="Pin")
        self.pin_button.connect("clicked", self.on_toggle_pin_active_session)
        top.append(self.pin_button)
        self.archive_button = Gtk.Button(label="Archiv")
        self.archive_button.connect("clicked", self.on_toggle_archive_active_session)
        top.append(self.archive_button)
        regenerate_button = Gtk.Button(label="Regenerieren")
        regenerate_button.connect("clicked", self.on_regenerate_active_session)
        top.append(regenerate_button)
        rename_button = Gtk.Button(label="Titel")
        rename_button.connect("clicked", self.on_rename_active_session)
        top.append(rename_button)
        delete_button = Gtk.Button(label="Loeschen")
        delete_button.connect("clicked", self.on_delete_active_session)
        top.append(delete_button)
        export_button = Gtk.Button(label="Export")
        export_button.connect("clicked", self.on_export)
        top.append(export_button)

        self.chat_view = Gtk.TextView()
        self.chat_view.add_css_class("telachat-text")
        self.chat_view.set_editable(False)
        self.chat_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.chat_buffer = self.chat_view.get_buffer()
        sc_chat = Gtk.ScrolledWindow()
        sc_chat.set_child(self.chat_view)
        sc_chat.set_vexpand(True)
        main.append(sc_chat)

        composer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        main.append(composer)
        self.input_view = Gtk.TextView()
        self.input_view.add_css_class("telachat-input")
        self.input_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.input_view.set_size_request(-1, 90)
        self.input_view.set_hexpand(True)
        input_keys = Gtk.EventControllerKey()
        input_keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        input_keys.connect("key-pressed", self.on_input_key_pressed)
        self.input_view.add_controller(input_keys)
        composer.append(self.input_view)
        self.send_button = Gtk.Button(label="Senden")
        self.send_button.connect("clicked", self.on_send)
        composer.append(self.send_button)
        self.cancel_button = Gtk.Button(label="Abbrechen")
        self.cancel_button.connect("clicked", self.cancel_active_request)
        self.cancel_button.set_sensitive(False)
        composer.append(self.cancel_button)
        self.command_popover = Gtk.Popover()
        self.command_popover.set_parent(self.input_view)
        self.command_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.command_popover.set_child(self.command_box)

        self.settings = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.settings.add_css_class("telachat-panel")
        self.settings.set_size_request(300, -1)
        self.settings.set_margin_top(14)
        self.settings.set_margin_bottom(14)
        self.settings.set_margin_start(10)
        self.settings.set_margin_end(14)
        self.inner_paned.set_end_child(self.settings)
        self.settings.append(Gtk.Label(label="Theme", xalign=0))
        self.theme_names = list(self.controller.theme_labels())
        theme_model = Gtk.StringList.new(
            [self.controller.theme_labels()[name] for name in self.theme_names]
        )
        self.theme_dropdown = Gtk.DropDown.new(theme_model, None)
        try:
            self.theme_dropdown.set_selected(self.theme_names.index(self.theme.name))
        except ValueError:
            self.theme_dropdown.set_selected(0)
        self.theme_dropdown.connect("notify::selected", self.on_theme_changed)
        self.settings.append(self.theme_dropdown)

        self.settings.append(Gtk.Label(label="Temperatur", xalign=0))
        self.temperature_spin = Gtk.SpinButton.new_with_range(0.0, 2.0, 0.1)
        self.temperature_spin.set_digits(2)
        self.settings.append(self.temperature_spin)

        self.settings.append(Gtk.Label(label="Max Tokens", xalign=0))
        self.max_tokens_spin = Gtk.SpinButton.new_with_range(1, 32768, 128)
        self.max_tokens_spin.set_digits(0)
        self.settings.append(self.max_tokens_spin)
        self.refresh_generation_defaults()

        self.settings.append(Gtk.Label(label="System", xalign=0))
        self.system_view = Gtk.TextView()
        self.system_view.add_css_class("telachat-input")
        self.system_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.system_buffer = self.system_view.get_buffer()
        self.system_buffer.set_text(self.controller.system_prompt())
        sc_system = Gtk.ScrolledWindow()
        sc_system.set_child(self.system_view)
        sc_system.set_vexpand(True)
        self.settings.append(sc_system)

        self.refresh_folders()
        self.refresh_tag_filter()
        self.refresh_sessions()
        if self.sessions:
            self.load_session(self.sessions[0].id)
        else:
            self.render_messages()
        self.window.present()
        GLib.idle_add(self._set_initial_panes)

    def _install_css(self) -> None:
        palette = self.theme.palette
        style_manager = Adw.StyleManager.get_default()
        if self.theme.name == "system" and "TELACHAT_SYSTEM_THEME" not in os.environ:
            high_contrast = getattr(style_manager, "get_high_contrast", lambda: False)()
            dark = getattr(style_manager, "get_dark", lambda: False)()
            if high_contrast:
                palette = theme_by_name("high-contrast").palette
            elif dark:
                palette = theme_by_name("dark").palette
        color_scheme = {
            "dark": "FORCE_DARK",
            "light": "FORCE_LIGHT",
        }.get(self.theme.adw_scheme, "DEFAULT")
        style_manager.set_color_scheme(getattr(Adw.ColorScheme, color_scheme))
        if not hasattr(self, "_theme_css_provider"):
            self._theme_css_provider = Gtk.CssProvider()
            display = Gdk.Display.get_default()
            if display is not None:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    self._theme_css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )
        self._theme_css_provider.load_from_data(
            f"""
            .telachat-window {{
                background-color: {palette.bg};
                color: {palette.text};
            }}
            .telachat-panel {{
                background-color: {palette.panel};
                color: {palette.text};
            }}
            .telachat-main {{
                background-color: {palette.bg};
                color: {palette.text};
            }}
            .telachat-text text {{
                background-color: {palette.surface};
                color: {palette.text};
            }}
            .telachat-input text {{
                background-color: {palette.input_bg};
                color: {palette.text};
            }}
            listbox row:selected {{
                background-color: {palette.selection};
                color: {palette.selection_fg};
            }}
            paned > separator {{
                background: {palette.sash};
                min-width: 12px;
                min-height: 12px;
            }}
            paned > separator:hover {{
                background: {palette.accent};
            }}
            """.encode()
        )

    def on_theme_changed(self, *_args: object) -> None:
        selected = self.theme_dropdown.get_selected()
        if selected < len(self.theme_names):
            self.theme = self.controller.set_theme(self.theme_names[selected])
            self._install_css()
            self.status.set_text(f"Theme: {self.theme.label}")

    def on_close(self, _window: Adw.ApplicationWindow) -> bool:
        if self.controller:
            self.controller.close()
        return False

    def selected_profile(self) -> str:
        selected = self.profile_dropdown.get_selected()
        if selected < len(self.profile_names):
            return self.profile_names[selected]
        return self.controller.default_profile_name()

    def selected_model(self) -> str:
        selected = self.model_dropdown.get_selected()
        if selected < len(self.model_names):
            return self.model_names[selected]
        return self.controller.config.profile(self.selected_profile()).model

    def selected_temperature(self) -> float:
        return float(self.temperature_spin.get_value())

    def selected_max_tokens(self) -> int:
        return int(self.max_tokens_spin.get_value_as_int())

    def refresh_models(self) -> None:
        profile = self.controller.config.profile(self.selected_profile())
        self.model_names = profile.models or [profile.model]
        self.model_dropdown.set_model(Gtk.StringList.new(self.model_names))
        try:
            selected = self.model_names.index(profile.model)
        except ValueError:
            selected = 0
        self.model_dropdown.set_selected(selected)
        self.refresh_generation_defaults()

    def refresh_generation_defaults(self) -> None:
        if not hasattr(self, "temperature_spin"):
            return
        profile = self.controller.config.profile(self.selected_profile())
        self.temperature_spin.set_value(profile.temperature)
        self.max_tokens_spin.set_value(profile.max_tokens)

    def update_model_choices_from_live(self, live_models: list[str]) -> None:
        selected = self.selected_model()
        merged = merge_model_choices(selected, live_models, self.model_names)
        if not merged:
            return
        self.model_names = merged
        self.model_dropdown.set_model(Gtk.StringList.new(self.model_names))
        self.model_dropdown.set_selected(
            self.model_names.index(selected) if selected in self.model_names else 0
        )

    def on_profile_changed(self, *_args: object) -> None:
        self.refresh_models()

    def select_session_backend(self, session: Session) -> None:
        try:
            selected_profile = self.profile_names.index(session.profile)
        except ValueError:
            selected_profile = -1
        if selected_profile >= 0:
            self.profile_dropdown.set_selected(selected_profile)
            self.refresh_models()
        model = session.model or self.controller.config.profile(self.selected_profile()).model
        if model and model not in self.model_names:
            self.model_names = [model, *self.model_names]
            self.model_dropdown.set_model(Gtk.StringList.new(self.model_names))
        if model in self.model_names:
            self.model_dropdown.set_selected(self.model_names.index(model))

    def on_filter_changed(self, *_args: object) -> None:
        self.refresh_sessions()
        if self.active_session is None:
            self.apply_selected_folder_prompt()

    def selected_sort(self) -> str:
        selected = self.sort_dropdown.get_selected()
        labels = list(self.sort_keys)
        if selected < len(labels):
            return self.sort_keys[labels[selected]]
        return "updated_desc"

    def selected_folder_id(self, *, for_new: bool = False) -> str | None:
        selected = self.folder_dropdown.get_selected()
        labels = list(self.folder_display_to_id)
        if selected >= len(labels):
            return None
        value = self.folder_display_to_id[labels[selected]]
        if value in {"__all__", "__none__"}:
            return None if for_new else value
        return value

    def selected_archive_filter(self) -> str:
        selected = self.archive_filter_dropdown.get_selected()
        labels = list(self.archive_filter_keys)
        if selected < len(labels):
            return self.archive_filter_keys[labels[selected]]
        return "active"

    def selected_tag_filter(self) -> str | None:
        selected = self.tag_filter_dropdown.get_selected()
        labels = list(self.tag_filter_values)
        if selected < len(labels):
            return self.tag_filter_values[labels[selected]]
        return None

    def selected_folder_value(self) -> str | None:
        selected = self.folder_dropdown.get_selected()
        labels = list(self.folder_display_to_id)
        if selected < len(labels):
            return self.folder_display_to_id[labels[selected]]
        return "__all__"

    def refresh_folders(self) -> None:
        selected_value = self.selected_folder_value() if hasattr(self, "folder_dropdown") else "__all__"
        self.folder_display_to_id = {"Alle": "__all__", "Ohne Ordner": "__none__"}
        for folder in self.controller.list_folders():
            self.folder_display_to_id[folder.name] = folder.id
        labels = list(self.folder_display_to_id)
        self.folder_dropdown.set_model(Gtk.StringList.new(labels))
        try:
            selected = list(self.folder_display_to_id.values()).index(selected_value)
        except ValueError:
            selected = 0
        self.folder_dropdown.set_selected(selected)

    def refresh_tag_filter(self) -> None:
        selected = self.tag_filter_dropdown.get_selected() if hasattr(self, "tag_filter_dropdown") else 0
        current = None
        labels = list(self.tag_filter_values)
        if selected < len(labels):
            current = self.tag_filter_values[labels[selected]]
        self.tag_filter_values = {"Alle Tags": None}
        for tag, count in self.controller.list_tags():
            self.tag_filter_values[f"#{tag} ({count})"] = tag
        labels = list(self.tag_filter_values)
        self.tag_filter_dropdown.set_model(Gtk.StringList.new(labels))
        values = list(self.tag_filter_values.values())
        self.tag_filter_dropdown.set_selected(values.index(current) if current in values else 0)

    def select_folder(self, folder_id: str | None) -> None:
        values = list(self.folder_display_to_id.values())
        try:
            selected = values.index("__none__" if folder_id is None else folder_id)
        except ValueError:
            selected = 0
        self.folder_dropdown.set_selected(selected)

    def selected_real_folder_id(self) -> str | None:
        selected = self.selected_folder_id(for_new=True)
        if selected:
            return selected
        return self.active_session.folder_id if self.active_session else None

    def system_prompt(self) -> str:
        start = self.system_buffer.get_start_iter()
        end = self.system_buffer.get_end_iter()
        return self.system_buffer.get_text(start, end, True).strip()

    def set_system_prompt(self, text: str) -> None:
        self.system_buffer.set_text(text)

    def apply_selected_folder_prompt(self) -> None:
        folder_id = self.selected_folder_id(for_new=True)
        if folder_id:
            self.set_system_prompt(self.controller.folder_system_prompt(folder_id))

    def on_save_selected_folder_prompt(self, _button: Gtk.Button) -> None:
        folder_id = self.selected_real_folder_id()
        if not folder_id:
            self.status.set_text("Ordner waehlen.")
            return
        folder = self.controller.set_folder_system_prompt(folder_id, self.system_prompt())
        self.status.set_text(f"Ordner-Prompt gespeichert: {folder.name}")

    def input_prompt(self) -> str:
        buffer = self.input_view.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        return buffer.get_text(start, end, True).strip()

    def clear_input(self) -> None:
        self.input_view.get_buffer().set_text("")

    def set_input_prompt(self, text: str) -> None:
        self.input_view.get_buffer().set_text(text)

    def selected_template_name(self) -> str | None:
        selected = self.template_dropdown.get_selected()
        if selected < len(self.template_names):
            return self.template_names[selected]
        return None

    def on_insert_template(self, _button: Gtk.Button) -> None:
        name = self.selected_template_name()
        if not name:
            self.status.set_text("Keine Vorlage gewaehlt.")
            return
        try:
            prompt = self.controller.apply_prompt_template(name, self.input_prompt())
        except KeyError as exc:
            self.status.set_text(str(exc))
            return
        self.set_input_prompt(prompt)
        self.status.set_text(f"Vorlage eingesetzt: {name}")

    def set_busy(self, busy: bool, text: str) -> None:
        self.status.set_text(text)
        self.send_button.set_sensitive(not busy)
        if hasattr(self, "cancel_button"):
            self.cancel_button.set_sensitive(busy)

    def refresh_sessions(self) -> None:
        self.sessions = self.controller.list_sessions(
            80,
            folder_id=self.selected_folder_id(),
            sort=self.selected_sort(),
            query=self.search_entry.get_text() if hasattr(self, "search_entry") else "",
            archive=self.selected_archive_filter(),
            tag=self.selected_tag_filter(),
        )
        while row := self.session_list.get_row_at_index(0):
            self.session_list.remove(row)
        for session in self.sessions:
            row = Gtk.ListBoxRow()
            row.session_id = session.id
            label = Gtk.Label(label=self.session_label(session), xalign=0)
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_margin_start(8)
            label.set_margin_end(8)
            row.set_child(label)
            self.session_list.append(row)

    def load_session(self, session_id: str) -> None:
        self.active_session, self.messages = self.controller.get_session(session_id)
        self.select_session_backend(self.active_session)
        self.set_system_prompt(self.active_session.system_prompt)
        self.update_active_title()
        self.render_messages()

    def render_messages(self) -> None:
        parts = []
        if not self.messages:
            parts.append("Bereit.\n")
        for message in self.messages:
            label = "Du" if message.role == "user" else "KI"
            parts.append(f"{label}\n{message.content}\n\n")
        self.chat_buffer.set_text("".join(parts))

    def session_label(self, session: Session) -> str:
        tags = " ".join(f"#{tag}" for tag in session.tags)
        suffix = f"  {tags}" if tags else ""
        markers = ("*" if session.pinned else " ") + ("A" if session.archived else " ")
        return f"{markers} {session.title}{suffix}"

    def update_active_title(self) -> None:
        if self.active_session:
            self.title_label.set_text(self.session_label(self.active_session))
            self.pin_button.set_label("Unpin" if self.active_session.pinned else "Pin")
            self.archive_button.set_label("Zurueck" if self.active_session.archived else "Archiv")
        else:
            self.title_label.set_text("Neue Unterhaltung")
            self.pin_button.set_label("Pin")
            self.archive_button.set_label("Archiv")

    def on_session_selected(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row is not None and hasattr(row, "session_id"):
            self.load_session(row.session_id)

    def on_new(self, _button: Gtk.Button) -> None:
        self.active_session, self.messages = self.controller.new_session(
            profile_name=self.selected_profile(),
            model=self.selected_model(),
            system_prompt=self.system_prompt(),
            folder_id=self.selected_folder_id(for_new=True),
        )
        self.update_active_title()
        self.refresh_sessions()
        self.set_system_prompt(self.active_session.system_prompt)
        self.render_messages()

    def on_send(self, _button: Gtk.Button) -> None:
        prompt = self.input_prompt()
        if not prompt:
            return
        if prompt.startswith("/"):
            self.clear_input()
            self.hide_command_suggestions()
            self.handle_command(prompt)
            return
        profile_name = self.selected_profile()
        model = self.selected_model()
        system_prompt = self.system_prompt()
        session_id = self.active_session.id if self.active_session else None
        folder_id = self.selected_folder_id(for_new=True)
        temperature = self.selected_temperature()
        max_tokens = self.selected_max_tokens()
        self.clear_input()
        self.hide_command_suggestions()
        operation_id = self.begin_operation("Denke...")
        threading.Thread(
            target=self._send_worker,
            args=(
                operation_id,
                prompt,
                profile_name,
                model,
                system_prompt,
                session_id,
                folder_id,
                temperature,
                max_tokens,
            ),
            daemon=True,
        ).start()

    def on_input_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        enter_pressed = keyval in {Gdk.KEY_Return, Gdk.KEY_KP_Enter}
        if keyval == Gdk.KEY_Escape:
            self.hide_command_suggestions()
            return False
        if keyval == Gdk.KEY_Tab:
            self.complete_slash_command()
            return True
        if enter_pressed and state & Gdk.ModifierType.SHIFT_MASK:
            self.on_send(self.send_button)
            return True
        GLib.idle_add(self.refresh_command_suggestions)
        return False

    def refresh_command_suggestions(self) -> bool:
        text = self.input_prompt()
        first_token = text.split(maxsplit=1)[0] if text.startswith("/") else ""
        suggestions = slash_command_suggestions(first_token)
        if not suggestions:
            self.hide_command_suggestions()
            return GLib.SOURCE_REMOVE
        while child := self.command_box.get_first_child():
            self.command_box.remove(child)
        self.current_command_suggestions = suggestions
        for item in suggestions:
            label = Gtk.Label(label=f"{item.usage}  -  {item.description}", xalign=0)
            label.set_margin_top(4)
            label.set_margin_bottom(4)
            label.set_margin_start(8)
            label.set_margin_end(8)
            self.command_box.append(label)
        self.command_popover.popup()
        return GLib.SOURCE_REMOVE

    def hide_command_suggestions(self) -> None:
        if hasattr(self, "command_popover"):
            self.command_popover.popdown()

    def complete_slash_command(self) -> None:
        text = self.input_prompt()
        first_token = text.split(maxsplit=1)[0] if text.startswith("/") else ""
        suggestions = slash_command_suggestions(first_token, limit=1)
        if not suggestions:
            self.refresh_command_suggestions()
            return
        rest = text.partition(" ")[2]
        self.set_input_prompt(f"{suggestions[0].name} {rest}".rstrip() + " ")
        self.hide_command_suggestions()

    def _send_worker(
        self,
        operation_id: int,
        prompt: str,
        profile_name: str,
        model: str,
        system_prompt: str,
        session_id: str | None,
        folder_id: str | None,
        temperature: float,
        max_tokens: int,
    ) -> None:
        try:
            payload = self.controller.send(
                session_id=session_id,
                profile_name=profile_name,
                model=model,
                system_prompt=system_prompt,
                prompt=prompt,
                folder_id=folder_id,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            GLib.idle_add(self._send_done, operation_id, payload)
        except Exception as exc:
            GLib.idle_add(self._error, operation_id, exc)

    def on_regenerate_active_session(self, _button: Gtk.Button) -> None:
        if not self.active_session:
            return
        operation_id = self.begin_operation("Generiere neu...")
        threading.Thread(
            target=self._regenerate_worker,
            args=(
                operation_id,
                self.active_session.id,
                self.selected_profile(),
                self.selected_model(),
                self.system_prompt(),
                self.selected_temperature(),
                self.selected_max_tokens(),
            ),
            daemon=True,
        ).start()

    def _regenerate_worker(
        self,
        operation_id: int,
        session_id: str,
        profile_name: str,
        model: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> None:
        try:
            payload = self.controller.regenerate(
                session_id=session_id,
                profile_name=profile_name,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            GLib.idle_add(self._send_done, operation_id, payload)
        except Exception as exc:
            GLib.idle_add(self._error, operation_id, exc)

    def _send_done(self, operation_id: int, payload: object) -> bool:
        if not self.operation_result_current(operation_id):
            return GLib.SOURCE_REMOVE
        self.active_session = payload.session
        self.messages = payload.messages
        self.update_active_title()
        self.refresh_sessions()
        self.render_messages()
        self.finish_operation(operation_id, self.response_status(payload))
        return GLib.SOURCE_REMOVE

    def begin_operation(self, text: str) -> int:
        self.operation_counter += 1
        operation_id = self.operation_counter
        self.active_operation_id = operation_id
        self.cancelled_operation_ids.discard(operation_id)
        self.set_busy(True, text)
        return operation_id

    def cancel_active_request(self, _button: Gtk.Button | None = None) -> None:
        operation_id = self.active_operation_id
        if operation_id is None:
            return
        self.cancelled_operation_ids.add(operation_id)
        self.active_operation_id = None
        self.set_busy(False, "Abgebrochen; Ergebnis wird ignoriert")

    def operation_result_current(self, operation_id: int) -> bool:
        if operation_id in self.cancelled_operation_ids:
            self.cancelled_operation_ids.discard(operation_id)
            return False
        return operation_id == self.active_operation_id

    def finish_operation(self, operation_id: int, text: str) -> None:
        self.cancelled_operation_ids.discard(operation_id)
        if operation_id == self.active_operation_id:
            self.active_operation_id = None
        self.set_busy(False, text)

    def response_status(self, payload: object) -> str:
        elapsed = getattr(payload, "elapsed_seconds", None)
        if isinstance(elapsed, (float, int)):
            return f"Antwort in {elapsed:.1f}s"
        return "Bereit"

    def on_doctor(self, _button: Gtk.Button) -> None:
        self.doctor()

    def doctor(self) -> None:
        profile_name = self.selected_profile()
        model = self.selected_model()
        operation_id = self.begin_operation("Pruefe...")
        threading.Thread(
            target=self._doctor_worker,
            args=(operation_id, profile_name, model),
            daemon=True,
        ).start()

    def _doctor_worker(self, operation_id: int, profile_name: str, model: str) -> None:
        try:
            models = self.controller.doctor(profile_name, model)
            GLib.idle_add(self._doctor_done, operation_id, models)
        except Exception as exc:
            GLib.idle_add(self._error, operation_id, exc)

    def _doctor_done(self, operation_id: int, models: list[str]) -> bool:
        if not self.operation_result_current(operation_id):
            return GLib.SOURCE_REMOVE
        self.update_model_choices_from_live(models)
        self.finish_operation(operation_id, "OK: " + (", ".join(models) or "Modelle erreichbar"))
        return GLib.SOURCE_REMOVE

    def on_create_folder(self, _button: Gtk.Button) -> None:
        self._entry_dialog(
            title="Ordner anlegen",
            label="Ordnername",
            initial="",
            callback=self.create_folder_from_name,
        )

    def create_folder_from_name(self, name: str) -> None:
        folder = self.controller.create_folder(name)
        self.refresh_folders()
        self.select_folder(folder.id)
        self.refresh_sessions()

    def _entry_dialog(
        self,
        *,
        title: str,
        label: str,
        initial: str,
        callback: object,
    ) -> None:
        dialog = Gtk.Window(title=title)
        dialog.set_transient_for(self.window)
        dialog.set_modal(True)
        dialog.set_default_size(340, 120)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(14)
        box.set_margin_end(14)
        dialog.set_child(box)
        entry = Gtk.Entry()
        entry.set_text(initial)
        box.append(Gtk.Label(label=label, xalign=0))
        box.append(entry)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_halign(Gtk.Align.END)
        box.append(row)
        cancel = Gtk.Button(label="Abbrechen")
        cancel.connect("clicked", lambda _button: dialog.close())
        row.append(cancel)
        save = Gtk.Button(label="Anlegen")

        def save_value(_button: Gtk.Button) -> None:
            value = entry.get_text().strip()
            if not value:
                self.status.set_text("Eingabe fehlt.")
                return
            callback(value)
            dialog.close()

        save.connect("clicked", save_value)
        row.append(save)
        dialog.present()

    def on_rename_selected_folder(self, _button: Gtk.Button) -> None:
        selected = self.selected_folder_value()
        labels = list(self.folder_display_to_id)
        selected_index = self.folder_dropdown.get_selected()
        if selected in {"__all__", "__none__", None} or selected_index >= len(labels):
            self.status.set_text("Ordner waehlen.")
            return

        def rename(name: str) -> None:
            folder = self.controller.rename_folder(selected, name)
            self.refresh_folders()
            self.select_folder(folder.id)
            self.refresh_sessions()

        self._entry_dialog(
            title="Ordner umbenennen",
            label="Neuer Ordnername",
            initial=labels[selected_index],
            callback=rename,
        )

    def on_delete_selected_folder(self, _button: Gtk.Button) -> None:
        selected = self.selected_folder_value()
        if selected in {"__all__", "__none__", None}:
            self.status.set_text("Ordner waehlen.")
            return
        dialog = Adw.MessageDialog.new(self.window, "Telachat", "Ordner loeschen?")
        dialog.add_response("cancel", "Abbrechen")
        dialog.add_response("delete", "Loeschen")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(_dialog: Adw.MessageDialog, response: str) -> None:
            if response == "delete":
                self.controller.delete_folder(selected)
                self.refresh_folders()
                self.folder_dropdown.set_selected(0)
                self.refresh_sessions()

        dialog.connect("response", on_response)
        dialog.present()

    def on_move_active_to_folder(self, _button: Gtk.Button) -> None:
        if not self.active_session:
            return
        selected = self.selected_folder_value()
        if selected == "__all__":
            self.status.set_text("Ordner waehlen oder /move NAME nutzen.")
            return
        folder_id = None if selected == "__none__" else selected
        self.active_session = self.controller.move_session(self.active_session.id, folder_id)
        self.refresh_sessions()
        self.status.set_text("Chat abgelegt.")

    def on_rename_active_session(self, _button: Gtk.Button) -> None:
        if not self.active_session:
            return

        def rename(title: str) -> None:
            self.active_session = self.controller.rename_session(self.active_session.id, title)
            self.update_active_title()
            self.refresh_sessions()

        self._entry_dialog(
            title="Chat umbenennen",
            label="Neuer Titel",
            initial=self.active_session.title,
            callback=rename,
        )

    def on_toggle_pin_active_session(self, _button: Gtk.Button) -> None:
        if not self.active_session:
            return
        self.active_session = self.controller.set_session_pinned(
            self.active_session.id,
            not self.active_session.pinned,
        )
        self.update_active_title()
        self.refresh_sessions()
        self.status.set_text("Chat angeheftet." if self.active_session.pinned else "Chat geloest.")

    def on_toggle_archive_active_session(self, _button: Gtk.Button) -> None:
        if not self.active_session:
            return
        self.active_session = self.controller.set_session_archived(
            self.active_session.id,
            not self.active_session.archived,
        )
        self.update_active_title()
        self.refresh_sessions()
        self.status.set_text(
            "Chat archiviert." if self.active_session.archived else "Chat wiederhergestellt."
        )

    def on_delete_active_session(self, _button: Gtk.Button) -> None:
        if not self.active_session:
            return
        dialog = Adw.MessageDialog.new(self.window, "Telachat", "Chat loeschen?")
        dialog.add_response("cancel", "Abbrechen")
        dialog.add_response("delete", "Loeschen")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(_dialog: Adw.MessageDialog, response: str) -> None:
            if response == "delete" and self.active_session:
                self.controller.delete_session(self.active_session.id)
                self._select_first_session_or_empty()

        dialog.connect("response", on_response)
        dialog.present()

    def _select_first_session_or_empty(self) -> None:
        self.refresh_sessions()
        if self.sessions:
            self.load_session(self.sessions[0].id)
        else:
            self.active_session = None
            self.messages = []
            self.update_active_title()
            self.render_messages()

    def on_toggle_sidebar(self, _button: Gtk.Button) -> None:
        self.sidebar.set_visible(not self.sidebar.get_visible())

    def on_toggle_settings(self, _button: Gtk.Button) -> None:
        self.settings.set_visible(not self.settings.get_visible())

    def _set_initial_panes(self) -> bool:
        width = max(self.window.get_width(), 1000)
        self.outer_paned.set_position(300)
        self.inner_paned.set_position(max(420, width - 620))
        return GLib.SOURCE_REMOVE

    def handle_command(self, raw: str) -> None:
        command, _, rest = raw.partition(" ")
        command = canonical_slash_command(command.lower())
        rest = rest.strip()
        if command == "/exit":
            self.window.close()
        elif command == "/help":
            dialog = Adw.MessageDialog.new(
                self.window,
                "Telachat Kommandos",
                slash_command_help(),
            )
            dialog.add_response("ok", "OK")
            dialog.present()
        elif command == "/new":
            self.on_new(self.send_button)
        elif command == "/rename":
            if rest and self.active_session:
                self.active_session = self.controller.rename_session(self.active_session.id, rest)
                self.update_active_title()
                self.refresh_sessions()
        elif command == "/delete":
            self.on_delete_active_session(self.send_button)
        elif command == "/pin":
            if self.active_session and not self.active_session.pinned:
                self.on_toggle_pin_active_session(self.send_button)
        elif command == "/unpin":
            if self.active_session and self.active_session.pinned:
                self.on_toggle_pin_active_session(self.send_button)
        elif command == "/archive":
            if self.active_session and not self.active_session.archived:
                self.on_toggle_archive_active_session(self.send_button)
        elif command == "/unarchive":
            if self.active_session and self.active_session.archived:
                self.on_toggle_archive_active_session(self.send_button)
        elif command == "/archives":
            labels = list(self.archive_filter_keys)
            self.archive_filter_dropdown.set_selected(labels.index("Archiv"))
            self.refresh_sessions()
            sessions = self.controller.list_sessions(20, archive="archived")
            self.status.set_text(
                " | ".join(f"{session.id} {session.title}" for session in sessions)
                or "Keine archivierten Sessions."
            )
        elif command == "/tag":
            if self.active_session:
                if rest:
                    try:
                        self.active_session = self.controller.add_session_tags(
                            self.active_session.id,
                            rest.split(),
                        )
                    except (KeyError, ValueError) as exc:
                        self.status.set_text(str(exc))
                        return
                    else:
                        self.update_active_title()
                        self.refresh_tag_filter()
                        self.refresh_sessions()
                self.status.set_text(
                    "Tags: "
                    + (
                        " ".join(f"#{tag}" for tag in self.active_session.tags)
                        if self.active_session.tags
                        else "-"
                    )
                )
        elif command == "/untag":
            if self.active_session:
                if rest:
                    try:
                        self.active_session = self.controller.remove_session_tags(
                            self.active_session.id,
                            rest.split(),
                        )
                    except (KeyError, ValueError) as exc:
                        self.status.set_text(str(exc))
                        return
                    else:
                        self.update_active_title()
                        self.refresh_tag_filter()
                        self.refresh_sessions()
                        self.status.set_text(
                            "Tags: "
                            + (
                                " ".join(f"#{tag}" for tag in self.active_session.tags)
                                if self.active_session.tags
                                else "-"
                            )
                        )
                else:
                    self.status.set_text("Nutzung: /untag TAG [TAG...]")
        elif command == "/tags":
            tags = self.controller.list_tags()
            self.status.set_text(", ".join(f"#{tag} ({count})" for tag, count in tags) or "Keine Tags.")
        elif command == "/stats":
            stats = self.controller.stats()
            dialog = Adw.MessageDialog.new(
                self.window,
                "Telachat Statistik",
                "\n".join(format_stats_lines(stats, include_database=False)),
            )
            dialog.add_response("ok", "OK")
            dialog.present()
            self.status.set_text(format_stats_summary(stats))
        elif command == "/context":
            estimate = estimate_context(
                self.messages,
                self.system_prompt(),
                max_history_messages=self.controller.config.max_history_messages,
            )
            dialog = Adw.MessageDialog.new(
                self.window,
                "Telachat Kontext",
                "\n".join(format_context_lines(estimate)),
            )
            dialog.add_response("ok", "OK")
            dialog.present()
            self.status.set_text(format_context_summary(estimate))
        elif command == "/doctor":
            self.doctor()
        elif command in {"/edit-last", "/edit"}:
            if not rest:
                self.status.set_text("Nutzung: /edit-last TEXT")
            elif self.active_session:
                try:
                    self.active_session, self.messages = self.controller.edit_last_user_message(
                        self.active_session.id,
                        rest,
                    )
                except (KeyError, ValueError) as exc:
                    self.status.set_text(str(exc))
                else:
                    self.refresh_sessions()
                    self.render_messages()
                    self.status.set_text("Letzte Nutzernachricht aktualisiert. /regen erzeugt neu.")
        elif command == "/fork":
            if self.active_session:
                self.active_session, self.messages = self.controller.fork_session(
                    self.active_session.id,
                    rest or None,
                )
                self.select_session_backend(self.active_session)
                self.set_system_prompt(self.active_session.system_prompt)
                self.update_active_title()
                self.refresh_sessions()
                self.render_messages()
                self.status.set_text(f"Fork geladen: {self.active_session.title}")
        elif command == "/regen":
            self.on_regenerate_active_session(self.send_button)
        elif command == "/templates":
            names = sorted(self.controller.prompt_templates())
            self.status.set_text("Vorlagen: " + (", ".join(names) or "keine"))
        elif command == "/template":
            template_name, _, text = rest.partition(" ")
            if not template_name:
                self.status.set_text("Nutzung: /template NAME TEXT")
            else:
                try:
                    prompt = self.controller.apply_prompt_template(template_name, text)
                except KeyError as exc:
                    self.status.set_text(str(exc))
                else:
                    self.set_input_prompt(prompt)
                    self.status.set_text(f"Vorlage eingesetzt: {template_name}")
        elif command == "/folder-system":
            folder_id = self.selected_real_folder_id()
            if not folder_id:
                self.status.set_text("Ordner waehlen.")
            elif rest:
                folder = self.controller.set_folder_system_prompt(folder_id, rest)
                self.set_system_prompt(folder.system_prompt)
                self.status.set_text(f"Ordner-Prompt gespeichert: {folder.name}")
            else:
                self.set_system_prompt(self.controller.folder_system_prompt(folder_id))
                self.status.set_text("Ordner-Prompt geladen.")
        elif command == "/folder":
            if rest:
                folder = self.controller.create_folder(rest)
                self.refresh_folders()
                self.select_folder(folder.id)
                self.refresh_sessions()
        elif command == "/rename-folder":
            selected = self.selected_folder_value()
            if rest and selected not in {"__all__", "__none__", None}:
                folder = self.controller.rename_folder(selected, rest)
                self.refresh_folders()
                self.select_folder(folder.id)
                self.refresh_sessions()
        elif command == "/delete-folder":
            self.on_delete_selected_folder(self.send_button)
        elif command == "/move":
            if rest and self.active_session:
                folder = self.controller.create_folder(rest)
                self.active_session = self.controller.move_session(self.active_session.id, folder.id)
                self.refresh_folders()
                self.select_folder(folder.id)
                self.refresh_sessions()
        elif command == "/unfile":
            if self.active_session:
                self.active_session = self.controller.move_session(self.active_session.id, None)
                self.select_folder(None)
                self.refresh_sessions()
        elif command == "/sort":
            mapping = {
                "newest": "Neueste zuerst",
                "oldest": "Aelteste zuerst",
                "title": "Titel A-Z",
                "title-desc": "Titel Z-A",
                "provider": "Provider",
            }
            label = mapping.get(rest)
            if label:
                labels = list(self.sort_keys)
                self.sort_dropdown.set_selected(labels.index(label))
                self.refresh_sessions()
        elif command == "/search":
            self.search_entry.set_text(rest)
            self.refresh_sessions()
        elif command == "/find":
            if not rest:
                self.status.set_text("Nutzung: /find TEXT")
            else:
                matches = format_message_matches(self.messages, rest)
                if matches:
                    dialog = Adw.MessageDialog.new(
                        self.window,
                        "Telachat Suche",
                        "\n".join(matches),
                    )
                    dialog.add_response("ok", "OK")
                    dialog.present()
                    self.status.set_text(f"Treffer: {len(matches)}")
                else:
                    self.status.set_text("Keine Treffer in der aktuellen Unterhaltung.")
        elif command == "/provider":
            for index, name in enumerate(self.profile_names):
                label = self.controller.profiles()[name].display_name
                if rest.lower() in {name.lower(), label.lower()}:
                    self.profile_dropdown.set_selected(index)
                    self.refresh_models()
                    break
        elif command == "/model":
            for index, model in enumerate(self.model_names):
                if rest.lower() == model.lower():
                    self.model_dropdown.set_selected(index)
                    break
        elif command == "/theme":
            if not rest:
                self.status.set_text(f"Theme: {self.theme.label}")
            else:
                try:
                    self.theme = self.controller.set_theme(rest)
                except ValueError as exc:
                    self.status.set_text(str(exc))
                else:
                    if self.theme.name in self.theme_names:
                        self.theme_dropdown.set_selected(self.theme_names.index(self.theme.name))
                    self._install_css()
                    self.status.set_text(f"Theme: {self.theme.label}")
        elif command == "/permissions":
            lines = [
                f"{name}: {redact_secret(profile.api_key)}"
                for name, profile in sorted(self.controller.profiles().items())
            ]
            dialog = Adw.MessageDialog.new(
                self.window,
                "Telachat Berechtigungen",
                "\n".join(lines),
            )
            dialog.add_response("ok", "OK")
            dialog.present()
        elif command in {"/left", "/links"}:
            self.sidebar.set_visible(not self.sidebar.get_visible())
        elif command == "/system":
            self.settings.set_visible(not self.settings.get_visible())
        else:
            self.status.set_text(f"Unbekanntes Kommando: {command}")

    def on_export(self, _button: Gtk.Button) -> None:
        if not self.active_session:
            return
        chooser = Gtk.FileChooserNative.new(
            "Export",
            self.window,
            Gtk.FileChooserAction.SAVE,
            "Speichern",
            "Abbrechen",
        )
        chooser.set_current_name(f"telachat-{self.active_session.id}.md")
        chooser.connect("response", self._export_response)
        chooser.show()

    def _export_response(self, chooser: Gtk.FileChooserNative, response: int) -> None:
        if response == Gtk.ResponseType.ACCEPT and self.active_session:
            file = chooser.get_file()
            path = file.get_path() if file else None
            if path:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(self.controller.export_markdown(self.active_session.id))
                self.status.set_text(f"Exportiert: {path}")
        chooser.destroy()

    def _error(self, operation_id: int, exc: Exception) -> bool:
        if not self.operation_result_current(operation_id):
            return GLib.SOURCE_REMOVE
        self.finish_operation(operation_id, "Fehler")
        dialog = Adw.MessageDialog.new(self.window, "Telachat", str(exc))
        dialog.add_response("ok", "OK")
        dialog.present()
        return GLib.SOURCE_REMOVE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="telachat-gtk")
    parser.parse_args(argv)
    app = GtkTelachatApp()
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
