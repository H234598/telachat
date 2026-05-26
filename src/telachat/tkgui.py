from __future__ import annotations

import argparse
import queue
import threading
import tkinter as tk
from collections.abc import Callable
from importlib.resources import as_file
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .assets import ICON_RANDOM, ICON_SYSTEM, icon_labels, icon_png_resource, random_icon_name
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
from .client import format_token_usage
from .config import ConfigError, redact_secret
from .controller import TelachatController
from .model_choices import merge_model_choices
from .skill_watchdog import set_runtime_skill_watchdog_enabled
from .store import Message, Session


class TkTelachatApp:
    def __init__(self) -> None:
        self.controller = TelachatController()
        set_runtime_skill_watchdog_enabled(self.controller.config.skill_watchdog_enabled)
        self.theme = self.controller.theme()
        self.active_session: Session | None = None
        self.messages: list[Message] = []
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.operation_counter = 0
        self.active_operation_id: int | None = None
        self.cancelled_operation_ids: set[int] = set()
        self.operation_prompt_drafts: dict[int, str] = {}
        self.app_icon_image: tk.PhotoImage | None = None
        self.current_random_icon: str | None = None
        self.icon_rotation_job: str | None = None
        self.chat_background_image: tk.PhotoImage | None = None
        self.folder_display_to_id: dict[str, str | None] = {}
        self.expanded_folder_ids: set[str] = set()
        self.session_rows: list[tuple[str, str | None]] = []
        self.tag_display_to_value: dict[str, str | None] = {"Alle Tags": None}
        self.sidebar_visible = True
        self.settings_visible = True
        self.sort_keys = {
            "Neueste zuerst": "updated_desc",
            "Älteste zuerst": "updated_asc",
            "Titel A-Z": "title_asc",
            "Titel Z-A": "title_desc",
            "Provider": "profile_asc",
        }
        self.archive_filter_keys = {
            "Aktiv": "active",
            "Archiv": "archived",
            "Alle": "all",
        }

        self.root = tk.Tk()
        self.root.title("Telachat Tk")
        self.root.geometry("1080x700")
        self.root.minsize(820, 540)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Configure>", self._on_resize)
        self._configure_style()
        self._build()
        self.refresh_profiles()
        self.refresh_tag_filter()
        self.refresh_sessions()
        sessions = self.controller.list_sessions(1)
        if sessions:
            self.load_session(sessions[0].id)
        else:
            self.render_messages()
        self.root.after(100, self._poll_events)

    def run(self) -> int:
        self.root.mainloop()
        return 0

    def _configure_style(self) -> None:
        palette = self.theme.palette
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background=palette.bg)
        style.configure("Sidebar.TFrame", background=palette.panel)
        style.configure("TLabel", background=palette.bg, foreground=palette.text)
        style.configure("Muted.TLabel", background=palette.bg, foreground=palette.muted)
        style.configure("Accent.TButton", padding=(12, 8))
        style.configure("TButton", padding=(10, 7))
        if hasattr(self, "root"):
            self.root.configure(bg=palette.bg)

    def _build(self) -> None:
        palette = self.theme.palette
        self._build_menu()
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.paned = tk.PanedWindow(
            self.root,
            orient=tk.HORIZONTAL,
            sashwidth=14,
            sashrelief=tk.RAISED,
            showhandle=True,
            handlesize=22,
            handlepad=70,
            opaqueresize=True,
            bg=palette.sash,
            borderwidth=0,
        )
        self.paned.grid(row=0, column=0, sticky="nsew")

        self.sidebar = ttk.Frame(self.paned, style="Sidebar.TFrame", padding=14, width=300)
        self.sidebar.rowconfigure(22, weight=1)

        title = ttk.Label(self.sidebar, text="Telachat", font=("Sans", 22, "bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="w")
        self.status = ttk.Label(self.sidebar, text="Bereit", style="Muted.TLabel")
        self.status.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 14))

        ttk.Label(self.sidebar, text="Provider").grid(row=2, column=0, sticky="w")
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(
            self.sidebar, textvariable=self.profile_var, state="readonly", width=24
        )
        self.profile_combo.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_changed)

        ttk.Label(self.sidebar, text="Modell").grid(row=4, column=0, sticky="w")
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(
            self.sidebar, textvariable=self.model_var, state="readonly", width=24
        )
        self.model_combo.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 10))

        ttk.Label(self.sidebar, text="Ordner").grid(row=6, column=0, sticky="w")
        self.folder_var = tk.StringVar()
        self.folder_combo = ttk.Combobox(
            self.sidebar, textvariable=self.folder_var, state="readonly", width=24
        )
        self.folder_combo.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        self.folder_combo.bind("<<ComboboxSelected>>", self.on_folder_filter_changed)

        ttk.Label(self.sidebar, text="Ansicht").grid(row=8, column=0, sticky="w")
        self.archive_filter_var = tk.StringVar(value="Aktiv")
        self.archive_filter_combo = ttk.Combobox(
            self.sidebar,
            textvariable=self.archive_filter_var,
            state="readonly",
            values=list(self.archive_filter_keys),
            width=24,
        )
        self.archive_filter_combo.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        self.archive_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_sessions())

        ttk.Label(self.sidebar, text="Tag").grid(row=10, column=0, sticky="w")
        self.tag_filter_var = tk.StringVar(value="Alle Tags")
        self.tag_filter_combo = ttk.Combobox(
            self.sidebar,
            textvariable=self.tag_filter_var,
            state="readonly",
            values=list(self.tag_display_to_value),
            width=24,
        )
        self.tag_filter_combo.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        self.tag_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_sessions())

        ttk.Label(self.sidebar, text="Sortierung").grid(row=12, column=0, sticky="w")
        self.sort_var = tk.StringVar(value="Neueste zuerst")
        self.sort_combo = ttk.Combobox(
            self.sidebar,
            textvariable=self.sort_var,
            state="readonly",
            values=list(self.sort_keys),
            width=24,
        )
        self.sort_combo.grid(row=13, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        self.sort_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_sessions())

        ttk.Label(self.sidebar, text="Suche").grid(row=14, column=0, sticky="w")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.sidebar, textvariable=self.search_var)
        self.search_entry.grid(row=15, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        self.search_entry.bind("<KeyRelease>", lambda _event: self.refresh_sessions())

        ttk.Label(self.sidebar, text="Vorlage").grid(row=16, column=0, sticky="w")
        self.template_var = tk.StringVar()
        self.template_combo = ttk.Combobox(
            self.sidebar,
            textvariable=self.template_var,
            state="readonly",
            values=list(self.controller.prompt_templates()),
            width=24,
        )
        self.template_combo.grid(row=17, column=0, sticky="ew", pady=(4, 0), padx=(0, 6))
        ttk.Button(self.sidebar, text="Einsetzen", command=self.insert_template).grid(
            row=17, column=1, sticky="ew", pady=(4, 0)
        )
        if self.controller.prompt_templates():
            self.template_var.set(next(iter(self.controller.prompt_templates())))

        ttk.Button(self.sidebar, text="Regenerieren", command=self.regenerate_active_session).grid(
            row=18, column=0, sticky="ew", padx=(0, 6), pady=(8, 0)
        )
        ttk.Button(self.sidebar, text="Check", command=self.doctor).grid(
            row=18, column=1, sticky="ew", pady=(8, 0)
        )
        ttk.Button(self.sidebar, text="Ordner +", command=self.create_folder_dialog).grid(
            row=19, column=0, sticky="ew", padx=(0, 6), pady=(8, 0)
        )
        ttk.Button(self.sidebar, text="Ablegen", command=self.move_active_to_folder).grid(
            row=19, column=1, sticky="ew", pady=(8, 0)
        )
        ttk.Button(self.sidebar, text="Ordner um", command=self.rename_selected_folder).grid(
            row=20, column=0, sticky="ew", padx=(0, 6), pady=(8, 0)
        )
        ttk.Button(self.sidebar, text="Ordner -", command=self.delete_selected_folder).grid(
            row=20, column=1, sticky="ew", pady=(8, 0)
        )
        ttk.Button(self.sidebar, text="Ordner-Prompt", command=self.save_selected_folder_prompt).grid(
            row=21, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )

        self.session_list = tk.Listbox(
            self.sidebar,
            width=32,
            borderwidth=0,
            highlightthickness=1,
            activestyle="none",
            bg=palette.surface,
            fg=palette.text,
            highlightbackground=palette.border,
            selectbackground=palette.selection,
            selectforeground=palette.selection_fg,
        )
        self.session_list.grid(row=22, column=0, columnspan=2, sticky="nsew", pady=(14, 0))
        self.session_list.bind("<<ListboxSelect>>", self._on_session_select)
        self.session_list.bind("<Double-Button-1>", self.on_session_row_double_click)
        self.session_list.bind("<Button-3>", self.show_session_context_menu)
        self.session_list.bind("<Button-2>", self.show_session_context_menu)

        self.main = ttk.Frame(self.paned, padding=16)
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(1, weight=1)

        top = ttk.Frame(self.main)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)
        self.sidebar_toggle_button = ttk.Button(
            top,
            text="◀",
            width=2,
            command=self.toggle_sidebar,
        )
        self.sidebar_toggle_button.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.session_title = ttk.Label(
            top,
            text="Neue Unterhaltung",
            font=("Sans", 16, "bold"),
            anchor="center",
        )
        self.session_title.grid(row=0, column=1, sticky="ew")
        self.session_title.bind("<Double-Button-1>", self.on_title_double_click)
        self.settings_toggle_button = ttk.Button(
            top,
            text="▶",
            width=2,
            command=self.toggle_settings,
        )
        self.settings_toggle_button.grid(row=0, column=2, sticky="e", padx=(8, 0))

        self.chat_text = tk.Text(
            self.main,
            wrap="word",
            state="disabled",
            borderwidth=0,
            padx=12,
            pady=12,
            bg=palette.surface,
            fg=palette.text,
            insertbackground=palette.text,
            highlightbackground=palette.border,
        )
        self.chat_text.grid(row=1, column=0, sticky="nsew", pady=12)
        self.chat_text.tag_configure("user", background=palette.user_bg, lmargin1=8, lmargin2=8)
        self.chat_text.tag_configure(
            "assistant", background=palette.assistant_bg, lmargin1=8, lmargin2=8
        )
        self.chat_text.tag_configure("role", foreground=palette.muted, font=("Sans", 9, "bold"))

        composer = ttk.Frame(self.main)
        composer.grid(row=2, column=0, sticky="ew")
        composer.columnconfigure(0, weight=1)
        self.input_text = tk.Text(
            composer,
            height=4,
            wrap="word",
            bg=palette.input_bg,
            fg=palette.text,
            insertbackground=palette.text,
            highlightbackground=palette.border,
        )
        self.input_text.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.input_text.bind("<Control-Return>", self._send_from_shortcut)
        self.input_text.bind("<Control-KP_Enter>", self._send_from_shortcut)
        self.input_text.bind("<Shift-Return>", self._send_from_shortcut)
        self.input_text.bind("<Shift-KP_Enter>", self._send_from_shortcut)
        self.input_text.bind("<KeyRelease>", self.on_input_changed)
        self.input_text.bind("<Tab>", self.complete_slash_command)
        self.input_text.bind("<Escape>", self.hide_command_suggestions)
        self.command_suggestions = tk.Listbox(
            composer,
            height=4,
            borderwidth=1,
            highlightthickness=1,
            bg=palette.surface,
            fg=palette.text,
            highlightbackground=palette.border,
            selectbackground=palette.selection,
            selectforeground=palette.selection_fg,
            activestyle="none",
        )
        self.command_suggestions.bind("<Double-Button-1>", self.on_command_suggestion_selected)
        self.command_suggestions.bind("<Return>", self.on_command_suggestion_selected)
        self.send_button = ttk.Button(composer, text="Senden", command=self.send_message)
        self.send_button.grid(row=0, column=1, sticky="ns")
        self.cancel_button = ttk.Button(
            composer,
            text="Abbrechen",
            command=self.cancel_active_request,
            state="disabled",
        )
        self.cancel_button.grid(row=0, column=2, sticky="ns", padx=(8, 0))

        self.settings = ttk.Frame(self.paned, padding=14, width=320)
        self.settings.rowconfigure(8, weight=1)
        ttk.Label(self.settings, text="Theme").grid(row=0, column=0, sticky="w")
        self.theme_display_to_name = {
            label: name for name, label in self.controller.theme_labels().items()
        }
        self.theme_var = tk.StringVar()
        self.theme_combo = ttk.Combobox(
            self.settings,
            textvariable=self.theme_var,
            state="readonly",
            values=list(self.theme_display_to_name),
            width=24,
        )
        self.theme_combo.grid(row=1, column=0, sticky="ew", pady=(4, 12))
        self.theme_combo.bind("<<ComboboxSelected>>", self.on_theme_changed)
        self.theme_var.set(self.controller.theme_labels()[self.theme.name])
        ttk.Label(self.settings, text="Temperatur").grid(row=2, column=0, sticky="w")
        self.temperature_var = tk.StringVar()
        self.temperature_spin = ttk.Spinbox(
            self.settings,
            from_=0.0,
            to=2.0,
            increment=0.1,
            textvariable=self.temperature_var,
            width=8,
        )
        self.temperature_spin.grid(row=3, column=0, sticky="ew", pady=(4, 10))
        ttk.Label(self.settings, text="Max Tokens").grid(row=4, column=0, sticky="w")
        self.max_tokens_var = tk.StringVar()
        self.max_tokens_spin = ttk.Spinbox(
            self.settings,
            from_=1,
            to=32768,
            increment=128,
            textvariable=self.max_tokens_var,
            width=8,
        )
        self.max_tokens_spin.grid(row=5, column=0, sticky="ew", pady=(4, 12))
        self.header_validation_var = tk.BooleanVar(
            value=self.controller.config.validate_profile_headers
        )
        ttk.Checkbutton(
            self.settings,
            text="Header pruefen",
            variable=self.header_validation_var,
            command=self.on_header_validation_changed,
        ).grid(row=6, column=0, sticky="w", pady=(0, 12))
        ttk.Label(self.settings, text="System").grid(row=7, column=0, sticky="w")
        self.system_text = tk.Text(
            self.settings,
            width=32,
            height=18,
            wrap="word",
            bg=palette.input_bg,
            fg=palette.text,
            insertbackground=palette.text,
            highlightbackground=palette.border,
        )
        self.system_text.grid(row=8, column=0, sticky="nsew", pady=(4, 0))
        self.system_text.insert("1.0", self.controller.system_prompt())
        self._apply_theme_to_widgets()
        self._apply_app_icon(force_random=self.controller.config.app_icon == ICON_RANDOM)
        self._apply_chat_background()
        self._layout_panes()
        self.root.after_idle(self._set_initial_sashes)

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Neu", command=self.new_session)
        file_menu.add_command(label="Regenerieren", command=self.regenerate_active_session)
        file_menu.add_separator()
        file_menu.add_command(label="Export", command=self.export_session)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.close)
        menu_bar.add_cascade(label="Datei", menu=file_menu)

        view_menu = tk.Menu(menu_bar, tearoff=False)
        view_menu.add_command(label="Linke Leiste umschalten", command=self.toggle_sidebar)
        view_menu.add_command(label="Systembereich umschalten", command=self.toggle_settings)
        menu_bar.add_cascade(label="Ansicht", menu=view_menu)

        options_menu = tk.Menu(menu_bar, tearoff=False)
        options_menu.add_command(label="Einstellungen...", command=self.open_options_dialog)
        menu_bar.add_cascade(label="Optionen", menu=options_menu)
        self.root.config(menu=menu_bar)

    def open_options_dialog(self) -> None:
        existing = getattr(self, "options_window", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_set()
            return

        dialog = tk.Toplevel(self.root)
        self.options_window = dialog
        dialog.title("Telachat Einstellungen")
        dialog.transient(self.root)
        dialog.minsize(460, 360)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(dialog)
        notebook.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        appearance = ttk.Frame(notebook, padding=14)
        appearance.columnconfigure(1, weight=1)
        notebook.add(appearance, text="Oberflaeche")

        ttk.Label(appearance, text="Theme").grid(row=0, column=0, sticky="w")
        self.options_theme_var = tk.StringVar(
            value=self.controller.theme_labels()[self.theme.name]
        )
        theme_combo = ttk.Combobox(
            appearance,
            textvariable=self.options_theme_var,
            state="readonly",
            values=list(self.theme_display_to_name),
        )
        theme_combo.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=(0, 10))
        theme_combo.bind("<<ComboboxSelected>>", self.on_options_theme_changed)

        ttk.Label(appearance, text="Icon").grid(row=1, column=0, sticky="w")
        self.icon_display_to_name = {
            label: name for name, label in icon_labels().items()
        }
        current_icon_label = self._label_for_icon(self.controller.config.app_icon)
        self.options_icon_var = tk.StringVar(value=current_icon_label)
        icon_combo = ttk.Combobox(
            appearance,
            textvariable=self.options_icon_var,
            state="readonly",
            values=list(self.icon_display_to_name),
        )
        icon_combo.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 10))
        icon_combo.bind("<<ComboboxSelected>>", self.on_options_icon_changed)

        ttk.Label(appearance, text="Chat-Hintergrund").grid(row=2, column=0, sticky="w")
        self.options_background_var = tk.StringVar(
            value=self.controller.config.chat_background_image
        )
        background_entry = ttk.Entry(
            appearance,
            textvariable=self.options_background_var,
            state="readonly",
        )
        background_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=(0, 10))
        background_buttons = ttk.Frame(appearance)
        background_buttons.grid(row=3, column=1, sticky="ew", padx=(10, 0))
        ttk.Button(
            background_buttons,
            text="Waehlen",
            command=self.choose_chat_background,
        ).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(
            background_buttons,
            text="Entfernen",
            command=self.clear_chat_background,
        ).grid(row=0, column=1)

        security = ttk.Frame(notebook, padding=14)
        security.columnconfigure(0, weight=1)
        notebook.add(security, text="Sicherheit")
        self.options_header_validation_var = tk.BooleanVar(
            value=self.controller.config.validate_profile_headers
        )
        ttk.Checkbutton(
            security,
            text="Profil-Header pruefen",
            variable=self.options_header_validation_var,
            command=self.on_options_header_validation_changed,
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.options_skill_watchdog_var = tk.BooleanVar(
            value=self.controller.config.skill_watchdog_enabled
        )
        ttk.Checkbutton(
            security,
            text="Skill-Watchdog beim Start und stuendlich ausfuehren",
            variable=self.options_skill_watchdog_var,
            command=self.on_options_skill_watchdog_changed,
        ).grid(row=1, column=0, sticky="w")

        button_row = ttk.Frame(dialog, padding=(12, 0, 12, 12))
        button_row.grid(row=1, column=0, sticky="ew")
        button_row.columnconfigure(0, weight=1)
        ttk.Button(button_row, text="Schliessen", command=dialog.destroy).grid(
            row=0,
            column=1,
            sticky="e",
        )

    def on_options_theme_changed(self, _event: object) -> None:
        self.theme_var.set(self.options_theme_var.get())
        self.on_theme_changed(_event)

    def on_options_icon_changed(self, _event: object) -> None:
        icon_name = self.icon_display_to_name.get(self.options_icon_var.get(), ICON_SYSTEM)
        try:
            icon_name = self.controller.set_app_icon(icon_name)
        except ValueError as exc:
            self.set_status(str(exc))
            return
        self.options_icon_var.set(self._label_for_icon(icon_name))
        self._apply_app_icon(force_random=icon_name == ICON_RANDOM)
        self.set_status(f"Icon: {self._label_for_icon(icon_name)}")

    def choose_chat_background(self) -> None:
        path = filedialog.askopenfilename(
            title="Chat-Hintergrund waehlen",
            filetypes=[
                ("Bilder", "*.png *.gif"),
                ("PNG", "*.png"),
                ("GIF", "*.gif"),
                ("Alle Dateien", "*.*"),
            ],
        )
        if not path:
            return
        background = self.controller.set_chat_background_image(path)
        self.options_background_var.set(background)
        self._apply_chat_background()
        self.render_messages()
        self.set_status("Chat-Hintergrund gespeichert.")

    def clear_chat_background(self) -> None:
        self.controller.set_chat_background_image("")
        self.options_background_var.set("")
        self._apply_chat_background()
        self.render_messages()
        self.set_status("Chat-Hintergrund entfernt.")

    def on_options_header_validation_changed(self) -> None:
        self.header_validation_var.set(self.options_header_validation_var.get())
        self.on_header_validation_changed()
        self.options_header_validation_var.set(self.header_validation_var.get())

    def on_options_skill_watchdog_changed(self) -> None:
        enabled = bool(self.options_skill_watchdog_var.get())
        enabled = self.controller.set_skill_watchdog_enabled(enabled)
        self.options_skill_watchdog_var.set(enabled)
        set_runtime_skill_watchdog_enabled(enabled)
        self.set_status(f"Skill-Watchdog: {'an' if enabled else 'aus'}")

    def _label_for_icon(self, icon_name: str) -> str:
        return icon_labels().get(icon_name, icon_labels()[ICON_SYSTEM])

    def _apply_app_icon(self, *, force_random: bool = False) -> None:
        icon_name = self.controller.config.app_icon
        if icon_name == ICON_RANDOM:
            if force_random or self.current_random_icon is None:
                icon_name = random_icon_name(self.current_random_icon)
                self.current_random_icon = icon_name
                self._set_tk_window_icon(icon_name)
            self._schedule_icon_rotation()
            return
        self._cancel_icon_rotation()
        self.current_random_icon = None
        if icon_name != ICON_SYSTEM:
            self._set_tk_window_icon(icon_name)

    def _set_tk_window_icon(self, icon_name: str) -> None:
        try:
            resource = icon_png_resource(icon_name)
            with as_file(resource) as path:
                image = tk.PhotoImage(file=str(path))
        except (OSError, tk.TclError, ValueError) as exc:
            self.set_status(f"Icon nicht geladen: {exc}")
            return
        self.app_icon_image = image
        self.root.iconphoto(True, image)

    def _schedule_icon_rotation(self) -> None:
        self._cancel_icon_rotation()
        self.icon_rotation_job = self.root.after(3_600_000, self._rotate_random_icon)

    def _cancel_icon_rotation(self) -> None:
        if self.icon_rotation_job is None:
            return
        try:
            self.root.after_cancel(self.icon_rotation_job)
        except tk.TclError:
            pass
        self.icon_rotation_job = None

    def _rotate_random_icon(self) -> None:
        self.icon_rotation_job = None
        if self.controller.config.app_icon == ICON_RANDOM:
            self._apply_app_icon(force_random=True)

    def _apply_chat_background(self) -> None:
        self.chat_background_image = None
        path = self.controller.config.chat_background_image
        if not path:
            return
        try:
            image = tk.PhotoImage(file=str(Path(path).expanduser()))
        except tk.TclError as exc:
            self.set_status(f"Chat-Hintergrund nicht geladen: {exc}")
            return
        self.chat_background_image = image

    def _apply_theme_to_widgets(self) -> None:
        palette = self.theme.palette
        self._configure_style()
        widgets = [
            getattr(self, "session_list", None),
            getattr(self, "chat_text", None),
            getattr(self, "input_text", None),
            getattr(self, "command_suggestions", None),
            getattr(self, "system_text", None),
        ]
        for widget in widgets:
            if widget is not None:
                options = {
                    "bg": palette.input_bg
                    if widget is self.input_text or widget is self.system_text
                    else palette.surface,
                    "fg": palette.text,
                    "highlightbackground": palette.border,
                    "selectbackground": palette.selection,
                    "selectforeground": palette.selection_fg,
                }
                if isinstance(widget, tk.Text):
                    options["insertbackground"] = palette.text
                widget.configure(
                    **options,
                )
        if hasattr(self, "paned"):
            self.paned.configure(bg=palette.sash)
        if hasattr(self, "chat_text"):
            self.chat_text.tag_configure("user", background=palette.user_bg)
            self.chat_text.tag_configure("assistant", background=palette.assistant_bg)
            self.chat_text.tag_configure("role", foreground=palette.muted)

    def on_theme_changed(self, _event: object) -> None:
        theme_name = self.theme_display_to_name.get(self.theme_var.get(), "system")
        self.theme = self.controller.set_theme(theme_name)
        self.theme_var.set(self.controller.theme_labels()[self.theme.name])
        self._apply_theme_to_widgets()
        self.set_status(f"Theme: {self.theme.label}")

    def on_header_validation_changed(self) -> None:
        enabled = bool(self.header_validation_var.get())
        try:
            enabled = self.controller.set_header_validation(enabled)
        except ConfigError as exc:
            self.header_validation_var.set(self.controller.config.validate_profile_headers)
            self.set_status(str(exc))
        else:
            self.header_validation_var.set(enabled)
            self.set_status(f"Header-Pruefung: {'an' if enabled else 'aus'}")

    def refresh_profiles(self) -> None:
        self.profile_display_to_name = {
            profile.display_name: name
            for name, profile in sorted(self.controller.profiles().items())
        }
        values = list(self.profile_display_to_name)
        self.profile_combo.configure(values=values)
        default_profile = self.controller.profiles()[self.controller.default_profile_name()]
        self.profile_var.set(default_profile.display_name)
        self.refresh_models()
        self.refresh_folders()

    def selected_profile(self) -> str:
        return self.profile_display_to_name.get(self.profile_var.get(), self.profile_var.get())

    def refresh_models(self) -> None:
        profile = self.controller.profiles()[self.selected_profile()]
        models = profile.models or [profile.model]
        self.model_combo.configure(values=models)
        self.model_var.set(profile.model)
        self.refresh_generation_defaults()

    def refresh_generation_defaults(self) -> None:
        if not hasattr(self, "temperature_var"):
            return
        profile = self.controller.profiles()[self.selected_profile()]
        self.temperature_var.set(f"{profile.temperature:.2f}".rstrip("0").rstrip("."))
        self.max_tokens_var.set(str(profile.max_tokens))

    def update_model_choices_from_live(self, live_models: list[str]) -> None:
        selected = self.model_var.get()
        configured = list(self.model_combo.cget("values"))
        merged = merge_model_choices(selected, live_models, configured)
        if not merged:
            return
        self.model_combo.configure(values=merged)
        self.model_var.set(selected if selected in merged else merged[0])

    def select_session_backend(self, session: Session) -> None:
        for label, name in self.profile_display_to_name.items():
            if name == session.profile:
                self.profile_var.set(label)
                self.refresh_models()
                break
        model = session.model or self.controller.profiles()[self.selected_profile()].model
        models = list(self.model_combo.cget("values"))
        if model and model not in models:
            models.insert(0, model)
            self.model_combo.configure(values=models)
        if model:
            self.model_var.set(model)

    def refresh_sessions(self) -> None:
        folder_filter = self.selected_folder_id()
        self.sessions = self.controller.list_sessions(
            80,
            folder_id=folder_filter,
            sort=self.sort_keys.get(self.sort_var.get(), "updated_desc"),
            query=self.search_var.get(),
            archive=self.selected_archive_filter(),
            tag=self.selected_tag_filter(),
        )
        self.session_list.delete(0, tk.END)
        self.session_rows = []
        if folder_filter in {"__all__", None}:
            self._insert_grouped_session_rows()
        elif folder_filter == "__none__":
            for session in self.sessions:
                self._insert_session_row(session)
        else:
            folder_name = self._folder_name(folder_filter) or "Ordner"
            self.expanded_folder_ids.add(folder_filter)
            self._insert_folder_row(folder_filter, folder_name)
            if folder_filter in self.expanded_folder_ids:
                for session in self.sessions:
                    self._insert_session_row(session, indent=True)

    def _insert_grouped_session_rows(self) -> None:
        folders = self.controller.list_folders()
        sessions_by_folder: dict[str | None, list[Session]] = {}
        for session in self.sessions:
            sessions_by_folder.setdefault(session.folder_id, []).append(session)
        for folder in folders:
            self._insert_folder_row(folder.id, folder.name)
            if folder.id in self.expanded_folder_ids:
                for session in sessions_by_folder.get(folder.id, []):
                    self._insert_session_row(session, indent=True)
        unfiled = sessions_by_folder.get(None, [])
        if unfiled:
            virtual_id = "__none__"
            self._insert_folder_row(virtual_id, "Ohne Ordner")
            if virtual_id in self.expanded_folder_ids:
                for session in unfiled:
                    self._insert_session_row(session, indent=True)

    def _insert_folder_row(self, folder_id: str, name: str) -> None:
        marker = "▾" if folder_id in self.expanded_folder_ids else "▸"
        self.session_rows.append(("folder", folder_id))
        self.session_list.insert(tk.END, f"{marker} {name}")

    def _insert_session_row(self, session: Session, *, indent: bool = False) -> None:
        self.session_rows.append(("session", session.id))
        prefix = "  " if indent else ""
        self.session_list.insert(tk.END, f"{prefix}{self._session_label(session)}")

    def _folder_name(self, folder_id: str | None) -> str | None:
        if folder_id == "__none__":
            return "Ohne Ordner"
        for folder in self.controller.list_folders():
            if folder.id == folder_id:
                return folder.name
        return None

    def load_session(self, session_id: str) -> None:
        self.active_session, self.messages = self.controller.get_session(session_id)
        self.select_session_backend(self.active_session)
        self.set_system_prompt_text(self.active_session.system_prompt)
        self.update_active_title()
        self.render_messages()

    def new_session(self, *, folder_id: str | None = None) -> None:
        title = simpledialog.askstring(
            "Telachat",
            "Name der Unterhaltung:",
            initialvalue="Neue Unterhaltung",
        )
        if title is None:
            return
        title = title.strip() or "Neue Unterhaltung"
        target_folder_id = self.selected_folder_id(for_new=True) if folder_id is None else folder_id
        self.active_session, self.messages = self.controller.new_session(
            profile_name=self.selected_profile(),
            model=self.model_var.get(),
            system_prompt=self.system_text.get("1.0", tk.END).strip(),
            title=title,
            folder_id=target_folder_id,
        )
        self.update_active_title()
        self.refresh_sessions()
        self.set_system_prompt_text(self.active_session.system_prompt)
        self.render_messages()

    def send_message(self) -> None:
        prompt = self.input_text.get("1.0", tk.END).strip()
        if not prompt:
            return
        if prompt.startswith("/"):
            self.input_text.delete("1.0", tk.END)
            self.hide_command_suggestions()
            self.handle_command(prompt)
            return
        profile_name = self.selected_profile()
        model = self.model_var.get()
        system_prompt = self.system_text.get("1.0", tk.END).strip()
        session_id = self.active_session.id if self.active_session else None
        folder_id = self.selected_folder_id(for_new=True)
        temperature = self.selected_temperature()
        max_tokens = self.selected_max_tokens()
        self.input_text.delete("1.0", tk.END)
        self.hide_command_suggestions()
        operation_id = self.begin_operation("Denke...", prompt)
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
            self.events.put(("sent", (operation_id, payload)))
        except Exception as exc:
            self.events.put(("error", (operation_id, exc)))

    def regenerate_active_session(self) -> None:
        if not self.active_session:
            return
        operation_id = self.begin_operation("Generiere neu...")
        threading.Thread(
            target=self._regenerate_worker,
            args=(
                operation_id,
                self.active_session.id,
                self.selected_profile(),
                self.model_var.get(),
                self.system_text.get("1.0", tk.END).strip(),
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
            self.events.put(("sent", (operation_id, payload)))
        except Exception as exc:
            self.events.put(("error", (operation_id, exc)))

    def _send_from_shortcut(self, _event: object) -> str:
        self.send_message()
        return "break"

    def on_input_changed(self, event: object) -> None:
        key = getattr(event, "keysym", "")
        if key in {"Tab", "Return", "KP_Enter", "Escape", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
            return
        self.refresh_command_suggestions()

    def refresh_command_suggestions(self) -> None:
        text = self.input_text.get("1.0", "end-1c")
        first_token = text.split(maxsplit=1)[0] if text.startswith("/") else ""
        suggestions = slash_command_suggestions(first_token)
        if not suggestions:
            self.hide_command_suggestions()
            return
        self.command_suggestions.delete(0, tk.END)
        for item in suggestions:
            self.command_suggestions.insert(tk.END, f"{item.usage}  -  {item.description}")
        self.command_suggestions.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(4, 0))
        self.command_suggestions.selection_set(0)

    def hide_command_suggestions(self, _event: object | None = None) -> str:
        self.command_suggestions.grid_remove()
        return "break"

    def complete_slash_command(self, _event: object) -> str:
        text = self.input_text.get("1.0", "end-1c")
        first_token = text.split(maxsplit=1)[0] if text.startswith("/") else ""
        suggestions = slash_command_suggestions(first_token)
        if not suggestions:
            self.refresh_command_suggestions()
            return "break"
        selection = self.command_suggestions.curselection()
        index = selection[0] if selection else 0
        command = suggestions[index].name if index < len(suggestions) else suggestions[0].name
        rest = text.partition(" ")[2]
        replacement = f"{command} {rest}".rstrip() + " "
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", replacement)
        self.hide_command_suggestions()
        return "break"

    def on_command_suggestion_selected(self, _event: object) -> None:
        self.complete_slash_command(_event)

    def doctor(self) -> None:
        operation_id = self.begin_operation("Pruefe...")
        threading.Thread(
            target=self._doctor_worker,
            args=(operation_id, self.selected_profile(), self.model_var.get()),
            daemon=True,
        ).start()

    def _doctor_worker(self, operation_id: int, profile_name: str, model: str) -> None:
        try:
            self.events.put(
                ("doctor", (operation_id, self.controller.doctor(profile_name, model)))
            )
        except Exception as exc:
            self.events.put(("error", (operation_id, exc)))

    def export_session(self) -> None:
        if not self.active_session:
            return
        target = filedialog.asksaveasfilename(
            defaultextension=".md",
            initialfile=f"telachat-{self.active_session.id}.md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All files", "*.*")],
        )
        if target:
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(self.controller.export_markdown(self.active_session.id))
            self.set_status(f"Exportiert: {target}")

    def insert_template(self) -> None:
        name = self.template_var.get()
        if not name:
            self.set_status("Keine Vorlage gewaehlt.")
            return
        try:
            prompt = self.controller.apply_prompt_template(
                name,
                self.input_text.get("1.0", tk.END).strip(),
            )
        except KeyError as exc:
            self.set_status(str(exc))
            return
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", prompt)
        self.set_status(f"Vorlage eingesetzt: {name}")

    def render_messages(self) -> None:
        self.chat_text.configure(state="normal")
        self.chat_text.delete("1.0", tk.END)
        if self.chat_background_image is not None:
            self.chat_text.image_create(tk.END, image=self.chat_background_image)
            self.chat_text.insert(tk.END, "\n\n")
        if not self.messages:
            self.chat_text.insert(tk.END, "Bereit.\n")
        for message in self.messages:
            label = "Du" if message.role == "user" else "KI"
            tag = "user" if message.role == "user" else "assistant"
            self.chat_text.insert(tk.END, f"{label}\n", ("role",))
            self.chat_text.insert(tk.END, f"{message.content}\n\n", (tag,))
        self.chat_text.configure(state="disabled")
        self.chat_text.see(tk.END)

    def _session_label(self, session: Session) -> str:
        tags = " ".join(f"#{tag}" for tag in session.tags)
        suffix = f"  {tags}" if tags else ""
        markers = ("*" if session.pinned else " ") + ("A" if session.archived else " ")
        return f"{markers} {session.title}{suffix}"

    def update_active_title(self) -> None:
        if self.active_session:
            self.session_title.configure(text=self.active_session.title)
        else:
            self.session_title.configure(text="Neue Unterhaltung")

    def on_title_double_click(self, _event: object) -> str:
        self.rename_active_session()
        return "break"

    def _on_session_select(self, _event: object) -> None:
        selected = self.session_list.curselection()
        if not selected:
            return
        row = self._session_row_at(selected[0])
        if row and row[0] == "session" and row[1]:
            self.load_session(row[1])

    def on_session_row_double_click(self, event: object) -> str | None:
        index = self._listbox_event_index(event)
        row = self._session_row_at(index)
        if not row:
            return None
        kind, item_id = row
        if kind == "folder" and item_id:
            if item_id in self.expanded_folder_ids:
                self.expanded_folder_ids.remove(item_id)
            else:
                self.expanded_folder_ids.add(item_id)
            self.refresh_sessions()
            return "break"
        if kind == "session" and item_id:
            self.load_session(item_id)
            return "break"
        return None

    def show_session_context_menu(self, event: object) -> str:
        index = self._listbox_event_index(event)
        row = self._session_row_at(index)
        menu = tk.Menu(self.root, tearoff=False)
        if row and row[0] == "session" and row[1]:
            self.session_list.selection_clear(0, tk.END)
            self.session_list.selection_set(index)
            self.load_session(row[1])
            menu.add_command(label="Regenerieren", command=self.regenerate_active_session)
            menu.add_command(label="Umbenennen", command=self.rename_active_session)
            menu.add_command(label="Anpinnen", command=self.toggle_pin_active_session)
            menu.add_command(label="Archiv", command=self.toggle_archive_active_session)
            menu.add_separator()
            menu.add_command(label="Ablegen", command=self.move_active_to_folder)
            menu.add_command(label="Export", command=self.export_session)
            menu.add_command(label="Loeschen", command=self.delete_active_session)
        elif row and row[0] == "folder" and row[1]:
            folder_id = row[1]
            label = "Zuklappen" if folder_id in self.expanded_folder_ids else "Aufklappen"
            menu.add_command(label=label, command=lambda: self.toggle_folder_row(folder_id))
            if folder_id != "__none__":
                menu.add_command(
                    label="Neue Unterhaltung hier",
                    command=lambda: self.new_session(folder_id=folder_id),
                )
                menu.add_command(
                    label="Ordner-Prompt",
                    command=lambda: self.with_folder_selection(
                        folder_id,
                        self.save_selected_folder_prompt,
                    ),
                )
                menu.add_command(
                    label="Ordner umbenennen",
                    command=lambda: self.with_folder_selection(
                        folder_id,
                        self.rename_selected_folder,
                    ),
                )
                menu.add_command(
                    label="Ordner loeschen",
                    command=lambda: self.with_folder_selection(
                        folder_id,
                        self.delete_selected_folder,
                    ),
                )
        else:
            menu.add_command(label="Neu", command=self.new_session)
            menu.add_command(label="Ordner anlegen", command=self.create_folder_dialog)
            menu.add_command(label="Check", command=self.doctor)
        try:
            menu.tk_popup(getattr(event, "x_root", 0), getattr(event, "y_root", 0))
        finally:
            menu.grab_release()
        return "break"

    def toggle_folder_row(self, folder_id: str) -> None:
        if folder_id in self.expanded_folder_ids:
            self.expanded_folder_ids.remove(folder_id)
        else:
            self.expanded_folder_ids.add(folder_id)
        self.refresh_sessions()

    def select_folder_filter(self, folder_id: str | None) -> None:
        wanted = "__none__" if folder_id is None else folder_id
        for label, value in self.folder_display_to_id.items():
            if value == wanted:
                self.folder_var.set(label)
                return

    def with_folder_selection(self, folder_id: str | None, action: Callable[[], None]) -> None:
        self.select_folder_filter(folder_id)
        action()

    def _session_row_at(self, index: int | None) -> tuple[str, str | None] | None:
        if index is None or index < 0 or index >= len(self.session_rows):
            return None
        return self.session_rows[index]

    def _listbox_event_index(self, event: object) -> int | None:
        y = getattr(event, "y", None)
        if y is None:
            return None
        index = self.session_list.nearest(y)
        bbox = self.session_list.bbox(index)
        if not bbox:
            return None
        top = bbox[1]
        bottom = top + bbox[3]
        if y < top or y > bottom:
            return None
        return index

    def _on_profile_changed(self, _event: object) -> None:
        self.refresh_models()

    def refresh_folders(self) -> None:
        self.folder_display_to_id = {"Alle": "__all__", "Ohne Ordner": "__none__"}
        for folder in self.controller.list_folders():
            self.folder_display_to_id[folder.name] = folder.id
        self.folder_combo.configure(values=list(self.folder_display_to_id))
        if not self.folder_var.get():
            self.folder_var.set("Alle")

    def refresh_tag_filter(self) -> None:
        current_value = self.selected_tag_filter() if hasattr(self, "tag_filter_var") else None
        self.tag_display_to_value = {"Alle Tags": None}
        for tag, count in self.controller.list_tags():
            self.tag_display_to_value[f"#{tag} ({count})"] = tag
        if hasattr(self, "tag_filter_combo"):
            self.tag_filter_combo.configure(values=list(self.tag_display_to_value))
            matching = [
                label
                for label, value in self.tag_display_to_value.items()
                if value == current_value
            ]
            if matching:
                self.tag_filter_var.set(matching[0])
            else:
                self.tag_filter_var.set("Alle Tags")

    def on_folder_filter_changed(self, _event: object) -> None:
        self.refresh_sessions()
        if self.active_session is None:
            self.apply_selected_folder_prompt()

    def selected_folder_id(self, *, for_new: bool = False) -> str | None:
        value = self.folder_display_to_id.get(self.folder_var.get(), "__all__")
        if value in {"__all__", "__none__"}:
            return None if for_new else value
        return value

    def selected_archive_filter(self) -> str:
        return self.archive_filter_keys.get(self.archive_filter_var.get(), "active")

    def selected_tag_filter(self) -> str | None:
        return self.tag_display_to_value.get(self.tag_filter_var.get())

    def selected_temperature(self) -> float:
        try:
            value = float(self.temperature_var.get().replace(",", "."))
        except ValueError:
            value = self.controller.profiles()[self.selected_profile()].temperature
        value = min(2.0, max(0.0, value))
        self.temperature_var.set(f"{value:.2f}".rstrip("0").rstrip("."))
        return value

    def selected_max_tokens(self) -> int:
        try:
            value = int(float(self.max_tokens_var.get()))
        except ValueError:
            value = self.controller.profiles()[self.selected_profile()].max_tokens
        value = min(32768, max(1, value))
        self.max_tokens_var.set(str(value))
        return value

    def selected_real_folder_id(self) -> str | None:
        selected = self.selected_folder_id(for_new=True)
        if selected:
            return selected
        return self.active_session.folder_id if self.active_session else None

    def set_system_prompt_text(self, text: str) -> None:
        self.system_text.delete("1.0", tk.END)
        self.system_text.insert("1.0", text)

    def apply_selected_folder_prompt(self) -> None:
        folder_id = self.selected_folder_id(for_new=True)
        if folder_id:
            self.set_system_prompt_text(self.controller.folder_system_prompt(folder_id))
            self.apply_selected_folder_backend(folder_id)

    def apply_selected_folder_backend(self, folder_id: str) -> None:
        profile_name, model = self.controller.folder_backend(folder_id)
        profile_applied = False
        if profile_name:
            for label, name in self.profile_display_to_name.items():
                if name == profile_name:
                    self.profile_var.set(label)
                    self.refresh_models()
                    profile_applied = True
                    break
        if model and (not profile_name or profile_applied):
            models = list(self.model_combo.cget("values"))
            if model not in models:
                models.insert(0, model)
                self.model_combo.configure(values=models)
            self.model_var.set(model)

    def save_selected_folder_prompt(self) -> None:
        folder_id = self.selected_real_folder_id()
        if not folder_id:
            self.set_status("Ordner waehlen.")
            return
        prompt = self.system_text.get("1.0", tk.END).strip()
        folder = self.controller.set_folder_system_prompt(folder_id, prompt)
        self.set_status(f"Ordner-Prompt gespeichert: {folder.name}")

    def create_folder_dialog(self) -> None:
        name = simpledialog.askstring("Telachat", "Ordnername:")
        if name:
            folder = self.controller.create_folder(name)
            self.refresh_folders()
            self.folder_var.set(folder.name)
            self.refresh_sessions()

    def rename_selected_folder(self) -> None:
        selected = self.folder_display_to_id.get(self.folder_var.get(), "__all__")
        if selected in {"__all__", "__none__", None}:
            self.set_status("Ordner waehlen.")
            return
        name = simpledialog.askstring("Telachat", "Neuer Ordnername:", initialvalue=self.folder_var.get())
        if name:
            folder = self.controller.rename_folder(selected, name)
            self.refresh_folders()
            self.folder_var.set(folder.name)
            self.refresh_sessions()

    def delete_selected_folder(self) -> None:
        selected = self.folder_display_to_id.get(self.folder_var.get(), "__all__")
        if selected in {"__all__", "__none__", None}:
            self.set_status("Ordner waehlen.")
            return
        if not messagebox.askyesno("Telachat", f"Ordner '{self.folder_var.get()}' loeschen?"):
            return
        self.controller.delete_folder(selected)
        self.refresh_folders()
        self.folder_var.set("Alle")
        self.refresh_sessions()

    def move_active_to_folder(self) -> None:
        if not self.active_session:
            return
        selected = self.folder_display_to_id.get(self.folder_var.get(), "__all__")
        if selected == "__all__":
            self.set_status("Ordner waehlen oder /move NAME nutzen.")
            return
        folder_id = None if selected == "__none__" else selected
        self.active_session = self.controller.move_session(self.active_session.id, folder_id)
        self.refresh_sessions()
        self.set_status("Chat abgelegt.")

    def rename_active_session(self) -> None:
        if not self.active_session:
            return
        title = simpledialog.askstring(
            "Telachat",
            "Neuer Titel:",
            initialvalue=self.active_session.title,
        )
        if title:
            self.active_session = self.controller.rename_session(self.active_session.id, title)
            self.update_active_title()
            self.refresh_sessions()

    def toggle_pin_active_session(self) -> None:
        if not self.active_session:
            return
        self.active_session = self.controller.set_session_pinned(
            self.active_session.id,
            not self.active_session.pinned,
        )
        self.update_active_title()
        self.refresh_sessions()
        self.set_status("Chat angeheftet." if self.active_session.pinned else "Chat geloest.")

    def toggle_archive_active_session(self) -> None:
        if not self.active_session:
            return
        self.active_session = self.controller.set_session_archived(
            self.active_session.id,
            not self.active_session.archived,
        )
        self.update_active_title()
        self.refresh_sessions()
        self.set_status(
            "Chat archiviert." if self.active_session.archived else "Chat wiederhergestellt."
        )

    def delete_active_session(self) -> None:
        if not self.active_session:
            return
        if not messagebox.askyesno("Telachat", f"Chat '{self.active_session.title}' loeschen?"):
            return
        self.controller.delete_session(self.active_session.id)
        self._select_first_session_or_empty()

    def _select_first_session_or_empty(self) -> None:
        self.refresh_sessions()
        if self.sessions:
            self.load_session(self.sessions[0].id)
        else:
            self.active_session = None
            self.messages = []
            self.update_active_title()
            self.render_messages()

    def toggle_sidebar(self) -> None:
        self.sidebar_visible = not self.sidebar_visible
        self._layout_panes()

    def toggle_settings(self) -> None:
        self.settings_visible = not self.settings_visible
        self._layout_panes()

    def _layout_panes(self) -> None:
        for pane in self.paned.panes():
            self.paned.forget(pane)
        if self.sidebar_visible:
            self.paned.add(self.sidebar, minsize=240, sticky="nsew")
        self.paned.add(self.main, minsize=380, sticky="nsew")
        if self.settings_visible:
            self.paned.add(self.settings, minsize=240, sticky="nsew")
        self._sync_pane_toggle_buttons()

    def _sync_pane_toggle_buttons(self) -> None:
        if hasattr(self, "sidebar_toggle_button"):
            self.sidebar_toggle_button.configure(text="◀" if self.sidebar_visible else "▶")
        if hasattr(self, "settings_toggle_button"):
            self.settings_toggle_button.configure(text="▶" if self.settings_visible else "◀")

    def _set_initial_sashes(self) -> None:
        try:
            width = max(self.root.winfo_width(), 900)
            panes = len(self.paned.panes())
            if self.sidebar_visible and panes >= 2:
                self.paned.sash_place(0, 300, 1)
            if self.sidebar_visible and self.settings_visible and panes >= 3:
                self.paned.sash_place(1, width - 320, 1)
            elif self.settings_visible and panes >= 2:
                self.paned.sash_place(0, width - 320, 1)
        except tk.TclError:
            pass

    def handle_command(self, raw: str) -> None:
        command, _, rest = raw.partition(" ")
        command = canonical_slash_command(command.lower())
        rest = rest.strip()
        if command == "/exit":
            self.root.destroy()
        elif command == "/help":
            messagebox.showinfo(
                "Telachat Kommandos",
                slash_command_help(),
            )
        elif command == "/new":
            self.new_session()
        elif command == "/rename":
            if rest and self.active_session:
                self.active_session = self.controller.rename_session(self.active_session.id, rest)
                self.update_active_title()
                self.refresh_sessions()
        elif command == "/delete":
            self.delete_active_session()
        elif command == "/pin":
            if self.active_session and not self.active_session.pinned:
                self.toggle_pin_active_session()
        elif command == "/unpin":
            if self.active_session and self.active_session.pinned:
                self.toggle_pin_active_session()
        elif command == "/archive":
            if self.active_session and not self.active_session.archived:
                self.toggle_archive_active_session()
        elif command == "/unarchive":
            if self.active_session and self.active_session.archived:
                self.toggle_archive_active_session()
        elif command == "/archives":
            self.archive_filter_var.set("Archiv")
            self.refresh_sessions()
            sessions = self.controller.list_sessions(20, archive="archived")
            self.set_status(
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
                        self.set_status(str(exc))
                        return
                    else:
                        self.update_active_title()
                        self.refresh_tag_filter()
                        self.refresh_sessions()
                self.set_status(
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
                        self.set_status(str(exc))
                        return
                    else:
                        self.update_active_title()
                        self.refresh_tag_filter()
                        self.refresh_sessions()
                        self.set_status(
                            "Tags: "
                            + (
                                " ".join(f"#{tag}" for tag in self.active_session.tags)
                                if self.active_session.tags
                                else "-"
                            )
                        )
                else:
                    self.set_status("Nutzung: /untag TAG [TAG...]")
        elif command == "/tags":
            tags = self.controller.list_tags()
            self.set_status(", ".join(f"#{tag} ({count})" for tag, count in tags) or "Keine Tags.")
        elif command == "/stats":
            stats = self.controller.stats()
            messagebox.showinfo(
                "Telachat Statistik",
                "\n".join(format_stats_lines(stats, include_database=False)),
            )
            self.set_status(format_stats_summary(stats))
        elif command == "/context":
            estimate = estimate_context(
                self.messages,
                self.system_text.get("1.0", tk.END).strip(),
                max_history_messages=self.controller.config.max_history_messages,
            )
            messagebox.showinfo(
                "Telachat Kontext",
                "\n".join(format_context_lines(estimate)),
            )
            self.set_status(format_context_summary(estimate))
        elif command == "/doctor":
            self.doctor()
        elif command in {"/edit-last", "/edit"}:
            if not rest:
                self.set_status("Nutzung: /edit-last TEXT")
            elif self.active_session:
                try:
                    self.active_session, self.messages = self.controller.edit_last_user_message(
                        self.active_session.id,
                        rest,
                    )
                except (KeyError, ValueError) as exc:
                    self.set_status(str(exc))
                else:
                    self.refresh_sessions()
                    self.render_messages()
                    self.set_status("Letzte Nutzernachricht aktualisiert. /regen erzeugt neu.")
        elif command == "/fork":
            if self.active_session:
                self.active_session, self.messages = self.controller.fork_session(
                    self.active_session.id,
                    rest or None,
                )
                self.select_session_backend(self.active_session)
                self.set_system_prompt_text(self.active_session.system_prompt)
                self.update_active_title()
                self.refresh_sessions()
                self.render_messages()
                self.set_status(f"Fork geladen: {self.active_session.title}")
        elif command == "/regen":
            self.regenerate_active_session()
        elif command == "/templates":
            names = sorted(self.controller.prompt_templates())
            self.set_status("Vorlagen: " + (", ".join(names) or "keine"))
        elif command == "/template":
            template_name, _, text = rest.partition(" ")
            if not template_name:
                self.set_status("Nutzung: /template NAME TEXT")
            else:
                try:
                    prompt = self.controller.apply_prompt_template(template_name, text)
                except KeyError as exc:
                    self.set_status(str(exc))
                else:
                    self.input_text.delete("1.0", tk.END)
                    self.input_text.insert("1.0", prompt)
                    self.set_status(f"Vorlage eingesetzt: {template_name}")
        elif command == "/folder-system":
            folder_id = self.selected_real_folder_id()
            if not folder_id:
                self.set_status("Ordner waehlen.")
            elif rest:
                folder = self.controller.set_folder_system_prompt(folder_id, rest)
                self.set_system_prompt_text(folder.system_prompt)
                self.set_status(f"Ordner-Prompt gespeichert: {folder.name}")
            else:
                self.set_system_prompt_text(self.controller.folder_system_prompt(folder_id))
                self.set_status("Ordner-Prompt geladen.")
        elif command == "/folder":
            if rest:
                folder = self.controller.create_folder(rest)
                self.refresh_folders()
                self.folder_var.set(folder.name)
                self.refresh_sessions()
        elif command == "/rename-folder":
            selected = self.folder_display_to_id.get(self.folder_var.get(), "__all__")
            if rest and selected not in {"__all__", "__none__", None}:
                folder = self.controller.rename_folder(selected, rest)
                self.refresh_folders()
                self.folder_var.set(folder.name)
                self.refresh_sessions()
        elif command == "/delete-folder":
            self.delete_selected_folder()
        elif command == "/move":
            if rest and self.active_session:
                folder = self.controller.create_folder(rest)
                self.active_session = self.controller.move_session(self.active_session.id, folder.id)
                self.refresh_folders()
                self.folder_var.set(folder.name)
                self.refresh_sessions()
        elif command == "/unfile":
            if self.active_session:
                self.active_session = self.controller.move_session(self.active_session.id, None)
                self.folder_var.set("Ohne Ordner")
                self.refresh_sessions()
        elif command == "/sort":
            mapping = {
                "newest": "Neueste zuerst",
                "oldest": "Älteste zuerst",
                "title": "Titel A-Z",
                "title-desc": "Titel Z-A",
                "provider": "Provider",
            }
            if rest in mapping:
                self.sort_var.set(mapping[rest])
                self.refresh_sessions()
        elif command == "/search":
            self.search_var.set(rest)
            self.refresh_sessions()
        elif command == "/find":
            if not rest:
                self.set_status("Nutzung: /find TEXT")
            else:
                matches = format_message_matches(self.messages, rest)
                if matches:
                    messagebox.showinfo("Telachat Suche", "\n".join(matches))
                    self.set_status(f"Treffer: {len(matches)}")
                else:
                    self.set_status("Keine Treffer in der aktuellen Unterhaltung.")
        elif command == "/provider":
            for label, name in self.profile_display_to_name.items():
                if rest.lower() in {label.lower(), name.lower()}:
                    self.profile_var.set(label)
                    self.refresh_models()
                    break
        elif command == "/models":
            if rest.lower() == "live":
                self.doctor()
            elif rest:
                self.set_status("Nutzung: /models [live]")
            else:
                models = list(self.model_combo.cget("values"))
                messagebox.showinfo(
                    "Telachat Modelle",
                    "\n".join(str(model) for model in models) if models else "Keine Modelle konfiguriert.",
                )
        elif command == "/model":
            models = list(self.model_combo.cget("values"))
            for model in models:
                if rest.lower() == str(model).lower():
                    self.model_var.set(model)
                    break
        elif command == "/theme":
            if not rest:
                self.set_status(f"Theme: {self.theme.label}")
            else:
                try:
                    self.theme = self.controller.set_theme(rest)
                except ValueError as exc:
                    self.set_status(str(exc))
                else:
                    self.theme_var.set(self.controller.theme_labels()[self.theme.name])
                    self._apply_theme_to_widgets()
                    self.set_status(f"Theme: {self.theme.label}")
        elif command == "/permissions":
            lines = [
                f"{name}: {redact_secret(profile.api_key)}"
                for name, profile in sorted(self.controller.profiles().items())
            ]
            messagebox.showinfo("Telachat Berechtigungen", "\n".join(lines))
        elif command in {"/left", "/links"}:
            self.toggle_sidebar()
        elif command == "/system":
            self.toggle_settings()
        else:
            self.set_status(f"Unbekanntes Kommando: {command}")

    def _on_resize(self, _event: object) -> None:
        self.chat_text.configure(height=max(12, self.root.winfo_height() // 32))

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "sent":
                    operation_id, result = payload
                    if not self.operation_result_current(operation_id):
                        continue
                    self.active_session = result.session
                    self.messages = result.messages
                    self.update_active_title()
                    self.refresh_sessions()
                    self.render_messages()
                    self.finish_operation(operation_id, self.response_status(result))
                elif kind == "doctor":
                    operation_id, models = payload
                    if not self.operation_result_current(operation_id):
                        continue
                    self.update_model_choices_from_live(models)
                    self.finish_operation(
                        operation_id,
                        "OK: " + (", ".join(models) or "Modelle erreichbar"),
                    )
                elif kind == "error":
                    operation_id, exc = payload
                    if not self.operation_result_current(operation_id):
                        continue
                    self.finish_operation(operation_id, "Fehler")
                    self.show_error(str(exc))
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def set_status(self, text: str) -> None:
        self.status.configure(text=text)

    def show_error(self, text: str) -> None:
        first_line = text.splitlines()[0] if text.splitlines() else "Unbekannter Fehler"
        self.set_status("Fehler: " + first_line)
        dialog = tk.Toplevel(self.root)
        dialog.title("Telachat Fehler")
        dialog.transient(self.root)
        dialog.minsize(520, 300)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)

        frame = ttk.Frame(dialog, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        text_view = tk.Text(frame, wrap="word", height=12)
        text_view.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_view.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        text_view.configure(yscrollcommand=scrollbar.set)
        text_view.insert("1.0", text)
        text_view.configure(state="disabled")
        text_view.focus_set()

        buttons = ttk.Frame(frame)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        buttons.columnconfigure(0, weight=1)
        ttk.Button(
            buttons,
            text="Kopieren",
            command=lambda: self.copy_to_clipboard(text),
        ).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(buttons, text="Schliessen", command=dialog.destroy).grid(
            row=0,
            column=2,
        )

    def copy_to_clipboard(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.set_status("In Zwischenablage kopiert.")

    def begin_operation(self, text: str, prompt_draft: str | None = None) -> int:
        self.operation_counter += 1
        operation_id = self.operation_counter
        self.active_operation_id = operation_id
        self.cancelled_operation_ids.discard(operation_id)
        if prompt_draft:
            self.operation_prompt_drafts[operation_id] = prompt_draft
        self.set_busy(True, text)
        return operation_id

    def cancel_active_request(self) -> None:
        operation_id = self.active_operation_id
        if operation_id is None:
            return
        draft = self.operation_prompt_drafts.pop(operation_id, None)
        if draft:
            self.restore_operation_prompt(draft)
        self.cancelled_operation_ids.add(operation_id)
        self.active_operation_id = None
        self.set_busy(False, "Abgebrochen; Ergebnis wird ignoriert")

    def operation_result_current(self, operation_id: int) -> bool:
        if operation_id in self.cancelled_operation_ids:
            self.cancelled_operation_ids.discard(operation_id)
            self.operation_prompt_drafts.pop(operation_id, None)
            return False
        if operation_id != self.active_operation_id:
            self.operation_prompt_drafts.pop(operation_id, None)
            return False
        return True

    def finish_operation(self, operation_id: int, text: str) -> None:
        self.cancelled_operation_ids.discard(operation_id)
        self.operation_prompt_drafts.pop(operation_id, None)
        if operation_id == self.active_operation_id:
            self.active_operation_id = None
        self.set_busy(False, text)

    def restore_operation_prompt(self, prompt: str) -> None:
        if self.input_text.get("1.0", "end-1c").strip():
            return
        self.input_text.insert("1.0", prompt)

    def response_status(self, payload: object) -> str:
        elapsed = getattr(payload, "elapsed_seconds", None)
        usage = format_token_usage(getattr(payload, "usage", None))
        if isinstance(elapsed, (float, int)):
            suffix = f" | {usage}" if usage else ""
            return f"Antwort in {elapsed:.1f}s{suffix}"
        return "Bereit"

    def set_busy(self, busy: bool, text: str) -> None:
        self.set_status(text)
        state = "disabled" if busy else "normal"
        self.send_button.configure(state=state)
        if hasattr(self, "cancel_button"):
            self.cancel_button.configure(state="normal" if busy else "disabled")

    def close(self) -> None:
        self.controller.close()
        self.root.destroy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="telachat-tk")
    parser.parse_args(argv)
    return TkTelachatApp().run()


if __name__ == "__main__":
    raise SystemExit(main())
