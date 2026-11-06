"""
Main Toolkit window (customtkinter).

Nothing on the screen is drawn by hand - it is all generated:

  Modules tab  <- the module list from modules.py
                  (groups, rows, hotkey hints, search)
  Config tab   <- the settings dict from settings.ini
                  (bool -> switch, everything else -> entry,
                   [HOTKEYS] from the hotkey service, [PROGRAMS] as a short list)

To add a utility you only add a Module to modules.py - a row appears by itself.
To add a setting you only add a key to settings.ini / DEFAULTS - a field appears by itself.

Optional: Module may have a `group` attribute ("Tools", "Games", ...).
Without it the group is guessed: "game" in keywords -> Games, "settings" -> System.
"""
from __future__ import annotations

import json
import sys
import tkinter as tk
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from scripts.hotkeys import parse_hotkey
from scripts.search import best_score
from scripts.settings_manager import _convert, write_settings
from scripts.time_tracker import format_hms, get_tracker


# ---------------------------------------------------------
# Look: one neutral palette + one accent. (light, dark) pairs.
# ---------------------------------------------------------

BG      = ("#f4f4f5", "#151515")
SURFACE = ("#ffffff", "#1d1d1d")
HOVER   = ("#e8e8ea", "#272727")
LINE    = ("#dcdce0", "#2c2c2c")
TEXT    = ("#18181b", "#e8e8e8")
MUTED   = ("#7a7a80", "#85858b")
ACCENT  = ("#2f6fed", "#5b9bff")
DANGER  = ("#c53030", "#ff6b6b")
OK      = ("#16803c", "#4ade80")

RADIUS = 8
PAGES = ("Modules", "Config")

GROUP_ORDER = ("Tools", "Games", "System")
COLLAPSED_BY_DEFAULT = ("Games",)

SECTION_TITLES = {
    "BASE": "General",
    "DIRS": "Folders",
    "HOTKEYS": "Hotkeys",
    "ARCHITECTURE": "Project layout",
    "PROGRAMS": "Work setup",
}
SECTION_ORDER = ("BASE", "DIRS", "HOTKEYS", "ARCHITECTURE")   # PROGRAMS is always last
RESTART_NEEDED = {("BASE", "hotkey")}                         # read once at startup
LABELS = {                                                    # nicer than "Hotkey" / "Working dir"
    ("BASE", "hotkey"): "Launcher hotkey",
    ("BASE", "log"): "Write log",
    ("DIRS", "working_dir"): "Working folder",
    ("DIRS", "temp_dir"): "Temp folder (inside working)",
    ("DIRS", "notes_dir"): "Notes folder",
}
OFF_WORDS = ("off", "none", "false")
MAX_PROGRAM_MATCHES = 8


# ---------------------------------------------------------
# Small persistent UI state (theme, collapsed groups, last tab)
# ---------------------------------------------------------

class UIState:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = {
            "appearance": "dark",
            "collapsed": list(COLLAPSED_BY_DEFAULT),
            "page": PAGES[0],
        }
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except (OSError, ValueError):
            pass

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            pass


class Fonts:
    def __init__(self):
        family = "Segoe UI" if sys.platform.startswith("win") else None
        self.title = ctk.CTkFont(family=family, size=17, weight="bold")
        self.body = ctk.CTkFont(family=family, size=13)
        self.small = ctk.CTkFont(family=family, size=11)
        self.caps = ctk.CTkFont(family=family, size=10, weight="bold")


def _pretty(key: str) -> str:
    return key.replace("_", " ").strip().capitalize()


def _section_title(section: str) -> str:
    return SECTION_TITLES.get(section, _pretty(section))


# ---------------------------------------------------------
# One clickable row: title on the left, hint (hotkey) on the right
# ---------------------------------------------------------

class Row(ctk.CTkFrame):
    def __init__(self, master, fonts: Fonts, title: str, hint: str, command):
        super().__init__(master, fg_color="transparent", corner_radius=RADIUS)
        self.grid_columnconfigure(0, weight=1)

        self._title = ctk.CTkLabel(self, text=title, anchor="w", font=fonts.body,
                                   text_color=TEXT)
        self._title.grid(row=0, column=0, sticky="ew", padx=(12, 6), pady=5)

        self._hint = ctk.CTkLabel(self, text=hint, font=fonts.small, text_color=MUTED)
        self._hint.grid(row=0, column=1, padx=(0, 12))

        for widget in (self, self._title, self._hint):
            widget.bind("<Enter>", self._enter, add="+")
            widget.bind("<Leave>", self._leave, add="+")
            widget.bind("<Button-1>", lambda _e: command(), add="+")

    def set_hint(self, text: str) -> None:
        self._hint.configure(text=text)

    def _enter(self, _event) -> None:
        self.configure(fg_color=HOVER)

    def _leave(self, _event) -> None:
        # moving from the row onto its own label also fires <Leave> - ignore that
        try:
            under = self.winfo_containing(*self.winfo_pointerxy())
        except (tk.TclError, KeyError):
            under = None

        while under is not None:
            if under is self:
                return
            under = getattr(under, "master", None)

        self.configure(fg_color="transparent")


class Caption(ctk.CTkLabel):
    """Small uppercase section caption; optionally clickable (collapsible groups)."""

    def __init__(self, master, fonts: Fonts, text: str, command=None):
        super().__init__(master, text=text, anchor="w", font=fonts.caps, text_color=MUTED)
        if command:
            self.bind("<Button-1>", lambda _e: command(), add="+")
            self.bind("<Enter>", lambda _e: self.configure(text_color=TEXT), add="+")
            self.bind("<Leave>", lambda _e: self.configure(text_color=MUTED), add="+")


# ---------------------------------------------------------
# Config tab - generated from the settings dict
# ---------------------------------------------------------

class ConfigPanel(ctk.CTkScrollableFrame):
    def __init__(self, master, fonts: Fonts, settings: dict, base_dir: Path,
                 get_service, toast, on_hotkeys_changed):
        super().__init__(master, fg_color="transparent",
                         scrollbar_button_color=HOVER,
                         scrollbar_button_hover_color=LINE)
        self.f = fonts
        self.settings = settings
        self.base_dir = Path(base_dir)
        self.get_service = get_service      # -> HotkeyService | None
        self.toast = toast                  # (text, error=False)
        self.on_hotkeys_changed = on_hotkeys_changed
        self._build()

    # ---- generation ----

    def _build(self) -> None:
        service = self.get_service()
        sections = [s for s in SECTION_ORDER if self.settings.get(s) or (s == "HOTKEYS" and service)]
        sections += [s for s in self.settings
                     if s not in SECTION_ORDER and s != "PROGRAMS" and self.settings[s]]

        for section in sections:
            self._caption(_section_title(section))

            if section == "HOTKEYS" and service:
                keys = list(service.actions) + [k for k in self.settings["HOTKEYS"]
                                                if k not in service.actions]
                for key in keys:
                    label = service.actions[key][0] if key in service.actions else _pretty(key)
                    self._field("HOTKEYS", key, service.combo_for(key), label)
            else:
                for key, value in self.settings.get(section, {}).items():
                    self._field(section, key, value, LABELS.get((section, key), _pretty(key)))

        if self.settings.get("PROGRAMS"):
            self._programs()

        ctk.CTkLabel(self, text="Changes are saved automatically.", anchor="w",
                     font=self.f.small, text_color=MUTED).pack(fill="x", padx=6, pady=(18, 6))

    def _caption(self, text: str) -> None:
        Caption(self, self.f, text.upper()).pack(fill="x", padx=6, pady=(16, 4))

    def _field(self, section: str, key: str, value, label: str) -> None:
        is_hotkey = section == "HOTKEYS" or "hotkey" in key.lower()

        if isinstance(value, bool) and not is_hotkey:
            self._switch(section, key, value, label)
        else:
            self._entry(section, key, value, label, is_hotkey)

    def _switch(self, section, key, value, label, parent=None) -> None:
        row = ctk.CTkFrame(parent or self, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=3)

        var = tk.BooleanVar(value=value)
        ctk.CTkLabel(row, text=label, anchor="w", font=self.f.body,
                     text_color=TEXT).pack(side="left", fill="x", expand=True)
        ctk.CTkSwitch(row, text="", width=42, variable=var, progress_color=ACCENT,
                      command=lambda: self.commit(section, key, bool(var.get()))
                      ).pack(side="right")

    def _entry(self, section, key, value, label, is_hotkey) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=3)

        ctk.CTkLabel(row, text=label, anchor="w", font=self.f.small,
                     text_color=MUTED).pack(fill="x")

        line = ctk.CTkFrame(row, fg_color="transparent")
        line.pack(fill="x", pady=(2, 0))

        entry = ctk.CTkEntry(line, height=30, corner_radius=RADIUS, font=self.f.body,
                             fg_color=SURFACE, border_color=LINE, border_width=1)
        entry.pack(side="left", fill="x", expand=True)

        shown = "off" if value is False else ("" if value is None else str(value))
        entry.insert(0, shown)
        state = {"last": shown}

        def apply(_event=None) -> None:
            text = entry.get().strip()
            if text == state["last"]:
                return

            new, error = self._parse(section, key, text, value, is_hotkey)
            if error:
                entry.configure(border_color=DANGER)
                self.toast(f"{label}: {error}", True)
                return

            if is_hotkey and text and text.lower() not in OFF_WORDS:
                text = new                      # canonical form, e.g. ctrl+alt+n -> Ctrl+Alt+N
                entry.delete(0, "end")
                entry.insert(0, text)

            entry.configure(border_color=LINE)
            state["last"] = text
            self.commit(section, key, new)

        entry.bind("<Return>", apply)
        entry.bind("<FocusOut>", apply)

        if section == "DIRS":
            def browse() -> None:
                chosen = filedialog.askdirectory(initialdir=entry.get() or str(self.base_dir))
                if chosen:
                    entry.delete(0, "end")
                    entry.insert(0, chosen)
                    apply()

            ctk.CTkButton(line, text="…", width=32, height=30, corner_radius=RADIUS,
                          fg_color=SURFACE, hover_color=HOVER, text_color=TEXT,
                          border_width=1, border_color=LINE, command=browse
                          ).pack(side="left", padx=(6, 0))

    @staticmethod
    def _parse(section, key, text, old, is_hotkey):
        """-> (value, error). Values are converted the same way settings.ini is read."""
        if is_hotkey:
            if not text:
                return "", None
            if text.lower() in OFF_WORDS:
                return False, None
            try:
                return parse_hotkey(text)[2], None
            except ValueError as error:
                return None, str(error)

        new = _convert(text)

        if isinstance(old, (int, float)) and not isinstance(old, bool):
            if isinstance(new, bool) or not isinstance(new, (int, float)):
                return None, "a number is expected"

        return new, None

    # ---- [PROGRAMS]: only enabled ones + search for the rest (the list can be 100+ long) ----

    def _programs(self) -> None:
        programs = self.settings["PROGRAMS"]

        self._caption(_section_title("PROGRAMS"))

        counter = ctk.CTkLabel(self, text="", anchor="w", font=self.f.small, text_color=MUTED)
        counter.pack(fill="x", padx=6)

        search = ctk.CTkEntry(self, height=30, corner_radius=RADIUS,
                              placeholder_text="Find a program to add…", font=self.f.body,
                              fg_color=SURFACE, border_color=LINE, border_width=1)
        search.pack(fill="x", padx=6, pady=(6, 4))

        holder = ctk.CTkFrame(self, fg_color="transparent")
        holder.pack(fill="x")

        def update_counter() -> None:
            enabled = sum(1 for v in programs.values() if v)
            counter.configure(text=f"{enabled} of {len(programs)} start with “Launch work setup”")

        def render(*_args) -> None:
            for child in holder.winfo_children():
                child.destroy()

            text = search.get().strip()
            names = [n for n, v in programs.items() if v]

            if text:
                scored = [(best_score(text, n), n) for n, v in programs.items() if not v]
                scored = sorted(((s, n) for s, n in scored if s is not None),
                                key=lambda t: (-t[0], t[1].lower()))
                names += [n for _, n in scored[:MAX_PROGRAM_MATCHES]]

            for name in names:
                self._switch("PROGRAMS", name, bool(programs[name]), name, parent=holder)

            if not names:
                ctk.CTkLabel(holder, text="Nothing enabled yet - type a name above.",
                             anchor="w", font=self.f.small, text_color=MUTED
                             ).pack(fill="x", padx=6, pady=4)

            update_counter()

        search.bind("<KeyRelease>", render, add="+")
        self._program_counter = update_counter
        render()

    # ---- saving ----

    def commit(self, section: str, key: str, value) -> None:
        self.settings.setdefault(section, {})[key] = value

        try:
            write_settings(self.base_dir, self.settings)
        except OSError as error:
            self.toast(f"Cannot save settings.ini: {error}", True)
            return

        if section == "PROGRAMS":
            getattr(self, "_program_counter", lambda: None)()
            self.toast("Saved")
            return

        if section == "HOTKEYS":
            self._apply_hotkeys(key)
            return

        note = " · restart to apply" if (section, key) in RESTART_NEEDED else ""
        self.toast("Saved" + note)

    def _apply_hotkeys(self, key: str) -> None:
        service = self.get_service()
        if service is None:
            self.toast("Saved")
            return

        status = service.apply()
        state, message = status.get(key, ("disabled", ""))
        title = service.actions[key][0] if key in service.actions else _pretty(key)

        if state == "error":
            self.toast(f"{title}: {message}", True)
        elif state == "ok":
            self.toast(f"Saved · {message}")
        else:
            self.toast(f"{title}: off")

        self.on_hotkeys_changed()


# ---------------------------------------------------------
# The window
# ---------------------------------------------------------

class MainWindow:
    def __init__(self, root: ctk.CTk, ctx, modules, problems=()):
        self.root = root
        self.ctx = ctx
        self.settings = ctx.settings
        self.base_dir = Path(ctx.base_dir)
        self.modules = [m for m in modules if m.key != "exit"]
        self.exit_module = next((m for m in modules if m.key == "exit"), None)
        self.problems = list(problems)

        self.state = UIState(self.base_dir / "db" / "ui_state.json")
        ctk.set_appearance_mode(self.state.data.get("appearance", "dark"))

        self.f = Fonts()
        self._toast_job = None
        self._visible: list = []
        self.rows: dict[str, Row] = {}
        self.captions: dict[str, Caption] = {}
        self.groups = self._group_modules()

        root.title("Toolkit")
        root.configure(fg_color=BG)
        root.geometry("380x680")
        root.minsize(340, 360)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_tabs()
        self._build_pages()
        self._build_footer()

        self.show_page(self.state.data.get("page", PAGES[0]))
        root.bind("<Map>", self._on_map, add="+")
        root.bind("<Control-f>", lambda _e: self._focus_search(), add="+")

        self._reset_status()
        self._tick()

    # ---- grouping ----

    @staticmethod
    def _group_of(module) -> str:
        explicit = getattr(module, "group", "")
        if explicit:
            return str(explicit)
        if "game" in {k.lower() for k in module.keywords}:
            return "Games"
        if module.key == "settings":
            return "System"
        return "Tools"

    def _group_modules(self) -> dict[str, list]:
        found: dict[str, list] = {}
        for module in self.modules:
            found.setdefault(self._group_of(module), []).append(module)

        ordered = {g: found.pop(g) for g in GROUP_ORDER if g in found}
        ordered.update(found)
        return ordered

    # ---- layout ----

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 0))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="Toolkit", font=self.f.title, text_color=TEXT,
                     anchor="w").grid(row=0, column=0, sticky="w")

        stats = ctk.CTkFrame(header, fg_color="transparent")
        stats.grid(row=0, column=1, sticky="e")

        self.todo_label = ctk.CTkLabel(stats, text="", font=self.f.small, text_color=MUTED)
        self.todo_label.pack(side="left", padx=(0, 10))
        self.timer_label = ctk.CTkLabel(stats, text="", font=self.f.small, text_color=MUTED)
        self.timer_label.pack(side="left")

        self._link(self.todo_label, "todo")
        self._link(self.timer_label, "time_tracker")

    def _link(self, label, key: str) -> None:
        module = next((m for m in self.modules if m.key == key), None)
        if module:
            label.bind("<Button-1>", lambda _e: self.run_module(module), add="+")

    def _build_tabs(self) -> None:
        self.tabs = ctk.CTkSegmentedButton(
            self.root, values=list(PAGES), command=self.show_page, height=30,
            corner_radius=RADIUS, font=self.f.body,
            fg_color=HOVER, selected_color=SURFACE, selected_hover_color=SURFACE,
            unselected_color=HOVER, unselected_hover_color=LINE,
            text_color=TEXT,
        )
        self.tabs.grid(row=1, column=0, sticky="ew", padx=18, pady=(12, 4))

    def _build_pages(self) -> None:
        # ---- Modules ----
        self.modules_page = ctk.CTkFrame(self.root, fg_color="transparent")
        self.modules_page.grid_columnconfigure(0, weight=1)
        self.modules_page.grid_rowconfigure(1, weight=1)

        self.search = ctk.CTkEntry(
            self.modules_page, height=34, corner_radius=RADIUS,
            placeholder_text="Search…", font=self.f.body,
            fg_color=SURFACE, border_color=LINE, border_width=1,
        )
        self.search.grid(row=0, column=0, sticky="ew", padx=18, pady=(6, 4))
        self.search.bind("<Return>", self._run_first)
        self.search.bind("<Escape>", self._escape)
        self.search.bind("<KeyRelease>", self._on_key, add="+")

        self.list = ctk.CTkScrollableFrame(
            self.modules_page, fg_color="transparent",
            scrollbar_button_color=HOVER, scrollbar_button_hover_color=LINE)
        self.list.grid(row=1, column=0, sticky="nsew", padx=(10, 4))

        for group, items in self.groups.items():
            self.captions[group] = Caption(self.list, self.f, "",
                                           command=lambda g=group: self._toggle_group(g))
            for module in items:
                self.rows[module.key] = Row(
                    self.list, self.f, module.title, self._hint_for(module),
                    lambda m=module: self.run_module(m))

        self.empty = ctk.CTkLabel(self.list, text="Nothing found", font=self.f.small,
                                  text_color=MUTED)
        self._render_modules()

        # ---- Config ----
        self.config_page = ConfigPanel(
            self.root, self.f, self.settings, self.base_dir,
            get_service=lambda: getattr(self.ctx, "hotkeys", None),
            toast=self.toast, on_hotkeys_changed=self.refresh_hints)

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self.root, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=14, pady=(2, 10))
        footer.grid_columnconfigure(0, weight=1)

        self.status = ctk.CTkLabel(footer, text="", anchor="w", font=self.f.small,
                                   text_color=MUTED)
        self.status.grid(row=0, column=0, sticky="ew", padx=4)

        def flat(text, command, width):
            return ctk.CTkButton(footer, text=text, width=width, height=26,
                                 corner_radius=RADIUS, font=self.f.small,
                                 fg_color="transparent", hover_color=HOVER,
                                 text_color=MUTED, command=command)

        flat("◐", self.toggle_theme, 28).grid(row=0, column=1)
        if self.exit_module:
            flat(self.exit_module.title, lambda: self.run_module(self.exit_module), 44
                 ).grid(row=0, column=2)

    # ---- pages ----

    def show_page(self, name: str) -> None:
        if name not in PAGES:
            name = PAGES[0]

        self.modules_page.grid_forget()
        self.config_page.grid_forget()

        if name == "Modules":
            self.modules_page.grid(row=2, column=0, sticky="nsew")
        else:
            self.config_page.grid(row=2, column=0, sticky="nsew", padx=(12, 6), pady=(4, 0))

        self.tabs.set(name)
        self.state.data["page"] = name
        self.state.save()

        if name == "Modules":
            self._focus_search()

    # ---- modules list ----

    def _hint_for(self, module) -> str:
        service = getattr(self.ctx, "hotkeys", None)
        combo = service.combo_for(module.key) if service else ""

        if not combo and module.key == "search":
            combo = str(self.settings.get("BASE", {}).get("hotkey", "") or "")

        if not combo or combo.lower() in OFF_WORDS:
            return ""

        try:
            return parse_hotkey(combo)[2]
        except ValueError:
            return combo

    def refresh_hints(self) -> None:
        for module in self.modules:
            self.rows[module.key].set_hint(self._hint_for(module))

    def _match(self, query: str, module):
        best = best_score(query, module.title)
        for word in module.keywords:
            score = best_score(query, word)
            if score is not None and (best is None or score - 150 > best):
                best = score - 150
        return best

    def _render_modules(self) -> None:
        for widget in self.list.winfo_children():
            widget.pack_forget()

        text = self.search.get().strip()
        self._visible = []

        if text:
            scored = [(self._match(text, m), i, m) for i, m in enumerate(self.modules)]
            scored = sorted((t for t in scored if t[0] is not None),
                            key=lambda t: (-t[0], t[1]))
            for _, _, module in scored:
                self._show_row(module)
            if not scored:
                self.empty.pack(pady=18)
            return

        collapsed = set(self.state.data.get("collapsed", []))
        for group, items in self.groups.items():
            closed = group in collapsed
            arrow = "▸" if closed else "▾"
            count = f"  ·  {len(items)}" if closed else ""
            caption = self.captions[group]
            caption.configure(text=f"{arrow}  {group.upper()}{count}")
            caption.pack(fill="x", padx=12, pady=(12, 2))

            if not closed:
                for module in items:
                    self._show_row(module)

    def _show_row(self, module) -> None:
        self.rows[module.key].pack(fill="x", padx=2, pady=1)
        self._visible.append(module)

    def _toggle_group(self, group: str) -> None:
        collapsed = set(self.state.data.get("collapsed", []))
        collapsed.symmetric_difference_update({group})
        self.state.data["collapsed"] = sorted(collapsed)
        self.state.save()
        self._render_modules()

    def _run_first(self, _event=None) -> None:
        if self._visible:
            self.run_module(self._visible[0])

    def _on_key(self, event) -> None:
        if event.keysym not in ("Return", "Escape"):
            self._render_modules()

    def _escape(self, _event=None) -> None:
        if self.search.get():
            self.search.delete(0, "end")
            self._render_modules()
        elif getattr(self.ctx, "tray", None):
            self.ctx.tray.hide_window()

    def _focus_search(self) -> None:
        if self.state.data.get("page") == "Modules":
            self.search.focus_set()

    def _on_map(self, event) -> None:
        if event.widget is self.root:
            self._focus_search()

    def run_module(self, module) -> None:
        try:
            module.run(self.ctx)
        except Exception as error:
            traceback.print_exc()
            self.toast(f"{module.title}: {error}", True)

    # ---- status line: toast / startup problems ----

    def toast(self, text: str, error: bool = False) -> None:
        if self._toast_job:
            self.root.after_cancel(self._toast_job)

        self.status.configure(text=text, text_color=DANGER if error else OK)
        self.status.unbind("<Button-1>")
        self._toast_job = self.root.after(3500, self._reset_status)

    def _reset_status(self) -> None:
        self._toast_job = None

        if self.problems:
            count = len(self.problems)
            self.status.configure(
                text=f"⚠ {count} startup problem{'s' if count > 1 else ''} - click for details",
                text_color=DANGER)
            self.status.bind("<Button-1>", lambda _e: messagebox.showwarning(
                "Toolkit", "\n".join(self.problems)), add="+")
        else:
            self.status.configure(text="", text_color=MUTED)

    # ---- theme ----

    def toggle_theme(self) -> None:
        current = ctk.get_appearance_mode().lower()
        new = "light" if current == "dark" else "dark"
        ctk.set_appearance_mode(new)
        self.state.data["appearance"] = new
        self.state.save()

    # ---- live stats (todo counter, running timer) ----

    def _tick(self) -> None:
        try:
            if self.root.winfo_viewable():
                self._refresh_stats()
        except tk.TclError:
            return                      # window destroyed
        except Exception:
            traceback.print_exc()

        self.root.after(1000, self._tick)

    def _refresh_stats(self) -> None:
        todos = getattr(self.ctx, "todos", None)
        if todos is not None:
            self.todo_label.configure(text=f"☑ {todos.counts()['active']}")

        running = None
        try:
            running = get_tracker(self.base_dir).running()
        except Exception:
            pass

        if running:
            elapsed = (datetime.now(running["started"].tzinfo) - running["started"]).total_seconds()
            self.timer_label.configure(
                text=f"● {running['project']}  {format_hms(elapsed)}", text_color=ACCENT)
        else:
            self.timer_label.configure(text="○ idle", text_color=MUTED)


def build_main_window(root, ctx, modules, problems=()) -> MainWindow:
    return MainWindow(root, ctx, modules, problems)
