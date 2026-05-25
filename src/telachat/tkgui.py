from __future__ import annotations

import argparse
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .commands import slash_command_help, slash_command_suggestions
from .config import redact_secret
from .controller import TelachatController
from .store import Message, Session


class TkTelachatApp:
    def __init__(self) -> None:
        self.controller = TelachatController()
        self.theme = self.controller.theme()
        self.active_session: Session | None = None
        self.messages: list[Message] = []
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.folder_display_to_id: dict[str, str | None] = {}
        self.sidebar_visible = True
        self.settings_visible = True
        self.sort_keys = {
            "Neueste zuerst": "updated_desc",
            "Älteste zuerst": "updated_asc",
            "Titel A-Z": "title_asc",
            "Titel Z-A": "title_desc",
            "Provider": "profile_asc",
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
        self.sidebar.rowconfigure(18, weight=1)

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

        ttk.Label(self.sidebar, text="Sortierung").grid(row=8, column=0, sticky="w")
        self.sort_var = tk.StringVar(value="Neueste zuerst")
        self.sort_combo = ttk.Combobox(
            self.sidebar,
            textvariable=self.sort_var,
            state="readonly",
            values=list(self.sort_keys),
            width=24,
        )
        self.sort_combo.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        self.sort_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_sessions())

        ttk.Label(self.sidebar, text="Suche").grid(row=10, column=0, sticky="w")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.sidebar, textvariable=self.search_var)
        self.search_entry.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        self.search_entry.bind("<KeyRelease>", lambda _event: self.refresh_sessions())

        ttk.Label(self.sidebar, text="Vorlage").grid(row=12, column=0, sticky="w")
        self.template_var = tk.StringVar()
        self.template_combo = ttk.Combobox(
            self.sidebar,
            textvariable=self.template_var,
            state="readonly",
            values=list(self.controller.prompt_templates()),
            width=24,
        )
        self.template_combo.grid(row=13, column=0, sticky="ew", pady=(4, 0), padx=(0, 6))
        ttk.Button(self.sidebar, text="Einsetzen", command=self.insert_template).grid(
            row=13, column=1, sticky="ew", pady=(4, 0)
        )
        if self.controller.prompt_templates():
            self.template_var.set(next(iter(self.controller.prompt_templates())))

        ttk.Button(self.sidebar, text="Neu", command=self.new_session).grid(
            row=14, column=0, sticky="ew", padx=(0, 6), pady=(8, 0)
        )
        ttk.Button(self.sidebar, text="Check", command=self.doctor).grid(
            row=14, column=1, sticky="ew", pady=(8, 0)
        )
        ttk.Button(self.sidebar, text="Ordner +", command=self.create_folder_dialog).grid(
            row=15, column=0, sticky="ew", padx=(0, 6), pady=(8, 0)
        )
        ttk.Button(self.sidebar, text="Ablegen", command=self.move_active_to_folder).grid(
            row=15, column=1, sticky="ew", pady=(8, 0)
        )
        ttk.Button(self.sidebar, text="Ordner um", command=self.rename_selected_folder).grid(
            row=16, column=0, sticky="ew", padx=(0, 6), pady=(8, 0)
        )
        ttk.Button(self.sidebar, text="Ordner -", command=self.delete_selected_folder).grid(
            row=16, column=1, sticky="ew", pady=(8, 0)
        )
        ttk.Button(self.sidebar, text="Ordner-Prompt", command=self.save_selected_folder_prompt).grid(
            row=17, column=0, columnspan=2, sticky="ew", pady=(8, 0)
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
        self.session_list.grid(row=18, column=0, columnspan=2, sticky="nsew", pady=(14, 0))
        self.session_list.bind("<<ListboxSelect>>", self._on_session_select)

        self.main = ttk.Frame(self.paned, padding=16)
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(1, weight=1)

        top = ttk.Frame(self.main)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(2, weight=1)
        ttk.Button(top, text="☰", command=self.toggle_sidebar).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(top, text="System", command=self.toggle_settings).grid(row=0, column=1, padx=(0, 8))
        self.session_title = ttk.Label(top, text="Neue Unterhaltung", font=("Sans", 16, "bold"))
        self.session_title.grid(row=0, column=2, sticky="w")
        self.pin_button = ttk.Button(top, text="Pin", command=self.toggle_pin_active_session)
        self.pin_button.grid(row=0, column=3, padx=(8, 0))
        ttk.Button(top, text="Regenerieren", command=self.regenerate_active_session).grid(
            row=0, column=4, padx=(8, 0)
        )
        ttk.Button(top, text="Titel", command=self.rename_active_session).grid(
            row=0, column=5, padx=(8, 0)
        )
        ttk.Button(top, text="Löschen", command=self.delete_active_session).grid(
            row=0, column=6, padx=(8, 0)
        )
        ttk.Button(top, text="Export", command=self.export_session).grid(row=0, column=7, padx=(8, 0))

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

        self.settings = ttk.Frame(self.paned, padding=14, width=320)
        self.settings.rowconfigure(3, weight=1)
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
        ttk.Label(self.settings, text="System").grid(row=2, column=0, sticky="w")
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
        self.system_text.grid(row=3, column=0, sticky="nsew", pady=(4, 0))
        self.system_text.insert("1.0", self.controller.system_prompt())
        self._apply_theme_to_widgets()
        self._layout_panes()
        self.root.after_idle(self._set_initial_sashes)

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
        self.sessions = self.controller.list_sessions(
            80,
            folder_id=self.selected_folder_id(),
            sort=self.sort_keys.get(self.sort_var.get(), "updated_desc"),
            query=self.search_var.get(),
        )
        self.session_list.delete(0, tk.END)
        for session in self.sessions:
            self.session_list.insert(tk.END, self._session_label(session))

    def load_session(self, session_id: str) -> None:
        self.active_session, self.messages = self.controller.get_session(session_id)
        self.select_session_backend(self.active_session)
        self.set_system_prompt_text(self.active_session.system_prompt)
        self.update_active_title()
        self.render_messages()

    def new_session(self) -> None:
        self.active_session, self.messages = self.controller.new_session(
            profile_name=self.selected_profile(),
            model=self.model_var.get(),
            system_prompt=self.system_text.get("1.0", tk.END).strip(),
            folder_id=self.selected_folder_id(for_new=True),
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
        self.input_text.delete("1.0", tk.END)
        self.hide_command_suggestions()
        self.set_busy(True, "Denke...")
        threading.Thread(
            target=self._send_worker,
            args=(prompt, profile_name, model, system_prompt, session_id, folder_id),
            daemon=True,
        ).start()

    def _send_worker(
        self,
        prompt: str,
        profile_name: str,
        model: str,
        system_prompt: str,
        session_id: str | None,
        folder_id: str | None,
    ) -> None:
        try:
            payload = self.controller.send(
                session_id=session_id,
                profile_name=profile_name,
                model=model,
                system_prompt=system_prompt,
                prompt=prompt,
                folder_id=folder_id,
            )
            self.events.put(("sent", payload))
        except Exception as exc:
            self.events.put(("error", exc))

    def regenerate_active_session(self) -> None:
        if not self.active_session:
            return
        self.set_busy(True, "Generiere neu...")
        threading.Thread(
            target=self._regenerate_worker,
            args=(
                self.active_session.id,
                self.selected_profile(),
                self.model_var.get(),
                self.system_text.get("1.0", tk.END).strip(),
            ),
            daemon=True,
        ).start()

    def _regenerate_worker(
        self,
        session_id: str,
        profile_name: str,
        model: str,
        system_prompt: str,
    ) -> None:
        try:
            payload = self.controller.regenerate(
                session_id=session_id,
                profile_name=profile_name,
                model=model,
                system_prompt=system_prompt,
            )
            self.events.put(("sent", payload))
        except Exception as exc:
            self.events.put(("error", exc))

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
        self.set_busy(True, "Pruefe...")
        threading.Thread(
            target=self._doctor_worker,
            args=(self.selected_profile(), self.model_var.get()),
            daemon=True,
        ).start()

    def _doctor_worker(self, profile_name: str, model: str) -> None:
        try:
            self.events.put(("doctor", self.controller.doctor(profile_name, model)))
        except Exception as exc:
            self.events.put(("error", exc))

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
        return ("* " if session.pinned else "  ") + session.title

    def update_active_title(self) -> None:
        if self.active_session:
            self.session_title.configure(text=self._session_label(self.active_session).strip())
            self.pin_button.configure(text="Unpin" if self.active_session.pinned else "Pin")
        else:
            self.session_title.configure(text="Neue Unterhaltung")
            self.pin_button.configure(text="Pin")

    def _on_session_select(self, _event: object) -> None:
        selected = self.session_list.curselection()
        if selected:
            self.load_session(self.sessions[selected[0]].id)

    def _on_profile_changed(self, _event: object) -> None:
        self.refresh_models()

    def refresh_folders(self) -> None:
        self.folder_display_to_id = {"Alle": "__all__", "Ohne Ordner": "__none__"}
        for folder in self.controller.list_folders():
            self.folder_display_to_id[folder.name] = folder.id
        self.folder_combo.configure(values=list(self.folder_display_to_id))
        if not self.folder_var.get():
            self.folder_var.set("Alle")

    def on_folder_filter_changed(self, _event: object) -> None:
        self.refresh_sessions()
        if self.active_session is None:
            self.apply_selected_folder_prompt()

    def selected_folder_id(self, *, for_new: bool = False) -> str | None:
        value = self.folder_display_to_id.get(self.folder_var.get(), "__all__")
        if value in {"__all__", "__none__"}:
            return None if for_new else value
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
        command = command.lower()
        rest = rest.strip()
        if command in {"/help", "/hilfe"}:
            messagebox.showinfo(
                "Telachat Kommandos",
                slash_command_help(),
            )
        elif command in {"/new", "/neu"}:
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
        elif command in {"/regen", "/regenerate"}:
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
        elif command in {"/folder", "/ordner"}:
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
        elif command in {"/move", "/ablegen"}:
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
        elif command == "/provider":
            for label, name in self.profile_display_to_name.items():
                if rest.lower() in {label.lower(), name.lower()}:
                    self.profile_var.set(label)
                    self.refresh_models()
                    break
        elif command == "/model":
            models = list(self.model_combo.cget("values"))
            for model in models:
                if rest.lower() == str(model).lower():
                    self.model_var.set(model)
                    break
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
                    self.active_session = payload.session
                    self.messages = payload.messages
                    self.update_active_title()
                    self.refresh_sessions()
                    self.render_messages()
                    self.set_busy(False, "Bereit")
                elif kind == "doctor":
                    self.set_busy(False, "OK: " + (", ".join(payload) or "Modelle erreichbar"))
                elif kind == "error":
                    self.set_busy(False, "Fehler")
                    messagebox.showerror("Telachat", str(payload))
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def set_status(self, text: str) -> None:
        self.status.configure(text=text)

    def set_busy(self, busy: bool, text: str) -> None:
        self.set_status(text)
        state = "disabled" if busy else "normal"
        self.send_button.configure(state=state)

    def close(self) -> None:
        self.controller.close()
        self.root.destroy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="telachat-tk")
    parser.parse_args(argv)
    return TkTelachatApp().run()


if __name__ == "__main__":
    raise SystemExit(main())
