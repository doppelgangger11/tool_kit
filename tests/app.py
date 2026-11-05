from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Any

import customtkinter as ctk

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "ui_config.json"
PROJECTS_PATH = ROOT / "projects.json"


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        path.write_text(json.dumps(fallback, ensure_ascii=False, indent=2), encoding="utf-8")
        return fallback
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class ActionDispatcher:
    """Maps config action names to Python handlers. UI never imports project internals."""
    def __init__(self, app: "ToolkitApp"):
        self.app = app
        self.handlers = {
            "show_notice": self.show_notice,
            "choose_file": self.choose_file,
            "run_demo": self.run_demo,
            "open_output": self.open_output,
            "refresh_projects": self.refresh_projects,
        }

    def dispatch(self, action: str, params: dict | None = None):
        handler = self.handlers.get(action)
        if handler is None:
            messagebox.showwarning("Unknown action", f"Action is not registered: {action}")
            return
        handler(params or {})

    def show_notice(self, params):
        messagebox.showinfo(params.get("title", "Toolkit"), params.get("message", "Action triggered."))

    def choose_file(self, params):
        path = filedialog.askopenfilename(
            title=params.get("title", "Select a file"),
            filetypes=[("All files", "*.*")]
        )
        if path:
            self.app.status_var.set(f"Selected: {Path(path).name}")
            self.app.selected_file = path
            if hasattr(self.app, "selected_file_label"):
                self.app.selected_file_label.configure(text=Path(path).name)

    def run_demo(self, params):
        project = params.get("project", self.app.active_project.get("name", "Project"))
        self.app.status_var.set(f"{project}: demo action completed")
        messagebox.showinfo("Demo action", f"{project}\n\nReplace this handler with your Core function.")

    def open_output(self, params):
        messagebox.showinfo("Output", "Connect this action to your output folder.")

    def refresh_projects(self, params):
        self.app.load_projects()
        self.app.render_project_list()


class ToolkitApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Personal Toolkit")
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.config_data = load_json(CONFIG_PATH, DEFAULT_CONFIG)
        self.projects_data = load_json(PROJECTS_PATH, DEFAULT_PROJECTS)
        self.projects: list[dict] = []
        self.active_project: dict = {}
        self.selected_file = ""

        self.status_var = tk.StringVar(value="Ready")
        self.dispatcher = ActionDispatcher(self)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()
        self.load_projects()
        self.show_dashboard()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(8, weight=1)
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="PERSONAL TOOLKIT", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(28, 4), sticky="w"
        )
        ctk.CTkLabel(self.sidebar, text="Automation workspace", text_color="gray").grid(
            row=1, column=0, padx=20, pady=(0, 28), sticky="w"
        )

        self._nav_button("Overview", self.show_dashboard, 2)
        self._nav_button("Projects", self.show_projects, 3)
        self._nav_button("Settings", self.show_settings, 4)

        ctk.CTkFrame(self.sidebar, height=1, fg_color=("gray80", "gray25")).grid(
            row=5, column=0, sticky="ew", padx=18, pady=22
        )
        ctk.CTkLabel(self.sidebar, text="WORKSPACE", text_color="gray", font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=6, column=0, padx=20, sticky="w"
        )
        self.sidebar_status = ctk.CTkLabel(self.sidebar, text="●  Local mode", text_color="#43b581")
        self.sidebar_status.grid(row=7, column=0, padx=20, pady=(8, 0), sticky="w")
        ctk.CTkLabel(self.sidebar, text="Prototype v0.1", text_color="gray").grid(
            row=9, column=0, padx=20, pady=20, sticky="sw"
        )

    def _nav_button(self, label, command, row):
        ctk.CTkButton(
            self.sidebar, text=label, anchor="w", height=40,
            fg_color="transparent", hover_color=("gray85", "gray20"),
            text_color=("gray15", "gray90"), command=command
        ).grid(row=row, column=0, padx=12, pady=4, sticky="ew")

    def _build_main_area(self):
        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray96", "#101318"))
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(24, 12))
        header.grid_columnconfigure(0, weight=1)
        self.page_title = ctk.CTkLabel(header, text="Overview", font=ctk.CTkFont(size=27, weight="bold"))
        self.page_title.grid(row=0, column=0, sticky="w")
        self.page_subtitle = ctk.CTkLabel(header, text="Your personal automation workspace", text_color="gray")
        self.page_subtitle.grid(row=1, column=0, sticky="w", pady=(3, 0))
        ctk.CTkButton(header, text="＋  Add project", width=130, command=self.add_project_dialog).grid(
            row=0, column=1, rowspan=2, padx=(10, 0)
        )

        self.content = ctk.CTkFrame(self.main, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=30, pady=(8, 16))
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        footer = ctk.CTkFrame(self.main, height=30, corner_radius=0, fg_color=("gray90", "#171b22"))
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(footer, textvariable=self.status_var, anchor="w", text_color="gray").grid(
            row=0, column=0, padx=18, pady=6, sticky="w"
        )
        self.theme_switch = ctk.CTkSwitch(footer, text="Dark", command=self.toggle_theme)
        self.theme_switch.select()
        self.theme_switch.grid(row=0, column=1, padx=18, pady=5)

    def _clear_content(self):
        for child in self.content.winfo_children():
            child.destroy()

    def _set_page(self, title, subtitle):
        self.page_title.configure(text=title)
        self.page_subtitle.configure(text=subtitle)

    def load_projects(self):
        self.projects = self.projects_data.get("projects", [])

    def show_dashboard(self):
        self._set_page("Overview", "Your personal automation workspace")
        self._clear_content()
        self.content.grid_columnconfigure((0, 1, 2), weight=1)

        stats = [
            ("Projects", str(len(self.projects)), "Registered in workspace"),
            ("Active", str(sum(p.get("status") == "Active" for p in self.projects)), "Ready to use"),
            ("UI engine", "Config-driven", "Widgets generated from JSON"),
        ]
        for col, (label, value, hint) in enumerate(stats):
            card = ctk.CTkFrame(self.content, corner_radius=14)
            card.grid(row=0, column=col, padx=(0 if col == 0 else 10, 0), pady=5, sticky="ew")
            ctk.CTkLabel(card, text=label, text_color="gray").pack(anchor="w", padx=18, pady=(16, 4))
            ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=23, weight="bold")).pack(anchor="w", padx=18)
            ctk.CTkLabel(card, text=hint, text_color="gray").pack(anchor="w", padx=18, pady=(3, 16))

        section = ctk.CTkFrame(self.content, corner_radius=14)
        section.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(18, 0))
        section.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(section, text="Recently used projects", font=ctk.CTkFont(size=17, weight="bold")).grid(
            row=0, column=0, padx=20, pady=18, sticky="w"
        )
        for i, project in enumerate(self.projects[:4], start=1):
            row = ctk.CTkFrame(section, fg_color=("gray94", "#1b2029"), corner_radius=10)
            row.grid(row=i, column=0, padx=16, pady=5, sticky="ew")
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=project["name"], font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=0, padx=14, pady=(10, 0), sticky="w"
            )
            ctk.CTkLabel(row, text=project.get("description", ""), text_color="gray").grid(
                row=1, column=0, padx=14, pady=(0, 10), sticky="w"
            )
            ctk.CTkButton(row, text="Open", width=75, command=lambda p=project: self.open_project(p)).grid(
                row=0, column=1, rowspan=2, padx=12
            )

    def show_projects(self):
        self._set_page("Projects", "Manage, launch and configure your automations")
        self.render_project_list()

    def render_project_list(self):
        self._clear_content()
        self.content.grid_columnconfigure(0, weight=1)
        for i, project in enumerate(self.projects):
            card = ctk.CTkFrame(self.content, corner_radius=13)
            card.grid(row=i, column=0, sticky="ew", pady=6)
            card.grid_columnconfigure(0, weight=1)
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 2))
            top.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(top, text=project["name"], font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(top, text=project.get("status", "Unknown"), text_color="#43b581").grid(row=0, column=1, padx=8)
            ctk.CTkLabel(card, text=project.get("description", ""), text_color="gray").grid(
                row=1, column=0, padx=16, pady=(0, 12), sticky="w"
            )
            ctk.CTkButton(card, text="Configure / Open", width=140, command=lambda p=project: self.open_project(p)).grid(
                row=0, column=1, rowspan=2, padx=16
            )

    def open_project(self, project):
        self.active_project = project
        self._set_page(project["name"], project.get("description", "Project workspace"))
        self._clear_content()
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self.content, corner_radius=14)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        ctk.CTkLabel(top, text=project.get("description", ""), text_color="gray").pack(
            anchor="w", padx=18, pady=(15, 4)
        )
        self.selected_file_label = ctk.CTkLabel(top, text="No file selected", text_color="gray")
        self.selected_file_label.pack(anchor="w", padx=18, pady=(0, 12))

        body = ctk.CTkFrame(self.content, corner_radius=14)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(body, text="Project controls", font=ctk.CTkFont(size=17, weight="bold")).pack(
            anchor="w", padx=20, pady=(18, 8)
        )

        config = project.get("ui", {})
        for widget in config.get("widgets", []):
            self._render_widget(body, widget)

        ctk.CTkLabel(body, text="Actions are resolved by ActionDispatcher; project Core stays independent.",
                     text_color="gray", wraplength=700).pack(anchor="w", padx=20, pady=(18, 16))

    def _render_widget(self, parent, spec):
        kind = spec.get("type", "button")
        label = spec.get("label", spec.get("text", "Control"))
        if kind == "button":
            ctk.CTkButton(
                parent, text=label, width=spec.get("width", 190),
                command=lambda a=spec.get("action", ""), p=spec.get("params", {}): self.dispatcher.dispatch(a, p)
            ).pack(anchor="w", padx=20, pady=6)
        elif kind == "label":
            ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=20, pady=6)
        elif kind == "entry":
            entry = ctk.CTkEntry(parent, placeholder_text=spec.get("placeholder", label), width=spec.get("width", 320))
            entry.pack(anchor="w", padx=20, pady=6)
        elif kind == "switch":
            switch = ctk.CTkSwitch(parent, text=label)
            switch.pack(anchor="w", padx=20, pady=6)
        elif kind == "separator":
            ctk.CTkFrame(parent, height=1, fg_color=("gray80", "gray30")).pack(fill="x", padx=20, pady=10)

    def show_settings(self):
        self._set_page("Settings", "Appearance and workspace configuration")
        self._clear_content()
        card = ctk.CTkFrame(self.content, corner_radius=14)
        card.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(card, text="Appearance", font=ctk.CTkFont(size=17, weight="bold")).pack(
            anchor="w", padx=20, pady=(18, 8)
        )
        ctk.CTkLabel(card, text="Use the Dark switch in the bottom bar to change appearance.", text_color="gray").pack(
            anchor="w", padx=20, pady=(0, 18)
        )
        ctk.CTkLabel(self.content, text=f"UI config: {CONFIG_PATH.name}\nProject registry: {PROJECTS_PATH.name}",
                     justify="left", text_color="gray").grid(row=1, column=0, sticky="w", pady=18)

    def toggle_theme(self):
        ctk.set_appearance_mode("dark" if self.theme_switch.get() else "light")

    def add_project_dialog(self):
        dialog = ctk.CTkInputDialog(text="Enter a project name:", title="Add project")
        name = dialog.get_input()
        if not name:
            return
        project = {
            "id": name.lower().replace(" ", "_"),
            "name": name,
            "description": "New project — edit projects.json to configure it.",
            "status": "Draft",
            "ui": {"widgets": [{"type": "button", "text": "Run", "action": "run_demo"}]}
        }
        self.projects.append(project)
        self.projects_data["projects"] = self.projects
        PROJECTS_PATH.write_text(json.dumps(self.projects_data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status_var.set(f"Project added: {name}")
        self.show_projects()


DEFAULT_CONFIG = {"appearance": "dark"}
DEFAULT_PROJECTS = {
    "projects": [
        {
            "id": "excel_cleaner",
            "name": "Excel Cleaner",
            "description": "Clean and normalize Excel / CSV files.",
            "status": "Active",
            "ui": {
                "widgets": [
                    {"type": "label", "text": "Input"},
                    {"type": "button", "text": "Select source file", "action": "choose_file"},
                    {"type": "separator"},
                    {"type": "entry", "label": "Output name", "placeholder": "cleaned_output.xlsx"},
                    {"type": "switch", "label": "Create backup"},
                    {"type": "button", "text": "Run cleaner", "action": "run_demo", "params": {"project": "Excel Cleaner"}},
                    {"type": "button", "text": "Open output folder", "action": "open_output"}
                ]
            }
        },
        {
            "id": "bank_reconcile",
            "name": "Bank Reconciliation",
            "description": "Match transactions and generate a reconciliation report.",
            "status": "Draft",
            "ui": {
                "widgets": [
                    {"type": "button", "text": "Select bank statement", "action": "choose_file"},
                    {"type": "button", "text": "Select ERP export", "action": "choose_file"},
                    {"type": "switch", "label": "Strict matching"},
                    {"type": "button", "text": "Run reconciliation", "action": "run_demo", "params": {"project": "Bank Reconciliation"}}
                ]
            }
        },
        {
            "id": "roberto",
            "name": "Roberto",
            "description": "Invoice collection, PDF parsing and matching pipeline.",
            "status": "Active",
            "ui": {
                "widgets": [
                    {"type": "button", "text": "Select PPR file", "action": "choose_file"},
                    {"type": "switch", "label": "Enable OCR fallback"},
                    {"type": "button", "text": "Run pipeline", "action": "run_demo", "params": {"project": "Roberto"}},
                    {"type": "button", "text": "View results", "action": "open_output"}
                ]
            }
        }
    ]
}


if __name__ == "__main__":
    app = ToolkitApp()
    app.mainloop()
