
from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
import urllib.error
import urllib.request

import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox


class DockerManagerWindow:
    """Docker Compose manager for Toolkit."""

    POLL_INTERVAL = 3000
    COMMAND_TIMEOUT = 120

    def __init__(self, root, base_dir, settings=None):
        self.root = root
        self.base_dir = Path(base_dir)
        self.settings = settings or {}

        self.db_path = self.base_dir / "db" / "docker_projects.json"
        self.projects = self._load_projects()
        self.selected_project = None
        self.selected_container = None

        self.events = queue.Queue()
        self.busy = False
        self.closed = False
        self.last_refresh = 0.0

        self.window = tk.Toplevel(root)
        self.window.title("Docker Manager")
        self.window.geometry("1100x700")
        self.window.minsize(850, 550)
        self.window.protocol("WM_DELETE_WINDOW", self._close)

        self._build_ui()
        self._refresh_project_list()

        if self.projects:
            self.project_list.selection_set(0)
            self._select_project()

        self._process_events()
        self._schedule_refresh()

    # --------------------------------------------------
    # PROJECT CONFIGURATION
    # --------------------------------------------------

    def _load_projects(self):
        try:
            data = json.loads(self.db_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def _save_projects(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.db_path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(self.projects, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.db_path)

    def _add_project(self):
        filename = filedialog.askopenfilename(
            parent=self.window,
            title="Select Docker Compose file",
            filetypes=[
                ("Compose files", "compose.yaml compose.yml "
                                  "docker-compose.yml docker-compose.yaml"),
                ("YAML files", "*.yaml *.yml"),
                ("All files", "*.*"),
            ],
        )
        if not filename:
            return

        compose_file = Path(filename).resolve()

        if not compose_file.is_file():
            messagebox.showerror("Docker Manager", "File not found.")
            return

        existing = next(
            (p for p in self.projects
             if Path(p["compose_file"]) == compose_file),
            None,
        )

        if existing:
            messagebox.showinfo("Docker Manager", "Project already added.")
            return

        project = {
            "name": compose_file.parent.name,
            "compose_file": str(compose_file),
            "url": "",
        }

        self.projects.append(project)
        self._save_projects()
        self._refresh_project_list()

        index = len(self.projects) - 1
        self.project_list.selection_set(index)
        self.project_list.see(index)
        self._select_project()

    def _remove_project(self):
        project = self._project()
        if not project:
            return

        if not messagebox.askyesno(
            "Remove project",
            f"Remove '{project['name']}' from Toolkit?\n\n"
            "Containers and files will NOT be deleted.",
            parent=self.window,
        ):
            return

        self.projects.remove(project)
        self._save_projects()
        self.selected_project = None
        self._refresh_project_list()
        self._clear_containers()
        self._set_status("Project removed from Toolkit.")

    def _edit_project(self):
        project = self._project()
        if not project:
            return

        dialog = tk.Toplevel(self.window)
        dialog.title("Project settings")
        dialog.geometry("520x190")
        dialog.transient(self.window)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Project name").pack(anchor="w")
        name_var = tk.StringVar(value=project["name"])
        ttk.Entry(frame, textvariable=name_var).pack(fill="x", pady=(3, 10))

        ttk.Label(frame, text="Web interface URL (optional)").pack(anchor="w")
        url_var = tk.StringVar(value=project.get("url", ""))
        ttk.Entry(frame, textvariable=url_var).pack(fill="x", pady=(3, 10))

        def save():
            name = name_var.get().strip()
            url = url_var.get().strip()

            if not name:
                messagebox.showwarning(
                    "Validation", "Project name is required.", parent=dialog
                )
                return

            if url and not url.startswith(("http://", "https://")):
                messagebox.showwarning(
                    "Validation",
                    "URL must start with http:// or https://",
                    parent=dialog,
                )
                return

            project["name"] = name
            project["url"] = url
            self._save_projects()
            self._refresh_project_list()
            self._select_project()
            dialog.destroy()

        ttk.Button(frame, text="Save", command=save).pack(anchor="e")

    def _project(self):
        selection = self.project_list.curselection()
        if not selection:
            return None

        index = selection[0]
        if index >= len(self.projects):
            return None

        return self.projects[index]

    def _refresh_project_list(self):
        current = self.selected_project
        self.project_list.delete(0, tk.END)

        for project in self.projects:
            self.project_list.insert(tk.END, project["name"])

        if current in self.projects:
            index = self.projects.index(current)
            self.project_list.selection_set(index)

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def _build_ui(self):
        self.window.columnconfigure(1, weight=1)
        self.window.rowconfigure(1, weight=1)

        header = ttk.Frame(self.window, padding=(12, 10))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")

        ttk.Label(
            header, text="DOCKER MANAGER", font=("Arial", 15, "bold")
        ).pack(side="left")

        self.connection_label = ttk.Label(
            header, text="Checking Docker..."
        )
        self.connection_label.pack(side="right")

        sidebar = ttk.Frame(self.window, padding=(10, 0, 8, 10))
        sidebar.grid(row=1, column=0, sticky="nsw")
        sidebar.rowconfigure(1, weight=1)

        ttk.Label(sidebar, text="COMPOSE PROJECTS").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )

        self.project_list = tk.Listbox(
            sidebar, width=25, exportselection=False, height=15
        )
        self.project_list.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.project_list.bind("<<ListboxSelect>>", self._on_project_selected)

        ttk.Button(
            sidebar, text="+ Add", command=self._add_project
        ).grid(row=2, column=0, sticky="ew", pady=(8, 0))

        ttk.Button(
            sidebar, text="Remove", command=self._remove_project
        ).grid(row=2, column=1, sticky="ew", padx=(5, 0), pady=(8, 0))

        ttk.Button(
            sidebar, text="Settings", command=self._edit_project
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        main = ttk.Frame(self.window, padding=(4, 0, 12, 10))
        main.grid(row=1, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)

        self.project_title = ttk.Label(
            main, text="Select a project", font=("Arial", 12, "bold")
        )
        self.project_title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        actions = ttk.Frame(main)
        actions.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.start_button = ttk.Button(
            actions, text="▶ Start", command=lambda: self._run_compose("up")
        )
        self.start_button.pack(side="left")

        self.stop_button = ttk.Button(
            actions, text="■ Stop", command=lambda: self._run_compose("stop")
        )
        self.stop_button.pack(side="left", padx=5)

        self.restart_button = ttk.Button(
            actions, text="↻ Restart", command=lambda: self._run_compose("restart")
        )
        self.restart_button.pack(side="left")

        ttk.Button(
            actions, text="Refresh", command=self._refresh
        ).pack(side="right")

        self.tree = ttk.Treeview(
            main,
            columns=("state", "health", "uptime", "exit"),
            show="tree headings",
            selectmode="browse",
        )
        self.tree.heading("#0", text="Container / Service")
        self.tree.heading("state", text="State")
        self.tree.heading("health", text="Health")
        self.tree.heading("uptime", text="Started")
        self.tree.heading("exit", text="Exit code")

        self.tree.column("#0", width=220, minwidth=140)
        self.tree.column("state", width=105, anchor="center")
        self.tree.column("health", width=110, anchor="center")
        self.tree.column("uptime", width=160, anchor="center")
        self.tree.column("exit", width=80, anchor="center")

        self.tree.grid(row=2, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_container_selected)

        self.tree.tag_configure("healthy", foreground="#16803c")
        self.tree.tag_configure("warning", foreground="#b7791f")
        self.tree.tag_configure("error", foreground="#c53030")

        details = ttk.LabelFrame(main, text="Diagnostics", padding=8)
        details.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        details.columnconfigure(0, weight=1)

        self.app_status = ttk.Label(
            details, text="Application: not checked"
        )
        self.app_status.grid(row=0, column=0, sticky="w")

        self.elapsed_label = ttk.Label(
            details, text="Last refresh: —"
        )
        self.elapsed_label.grid(row=1, column=0, sticky="w", pady=(3, 0))

        detail_buttons = ttk.Frame(details)
        detail_buttons.grid(row=0, column=1, rowspan=2, padx=(8, 0))

        ttk.Button(
            detail_buttons, text="Container logs", command=self._show_logs
        ).pack(side="left")

        ttk.Button(
            detail_buttons, text="Open web UI", command=self._open_web_ui
        ).pack(side="left", padx=(5, 0))

        footer = ttk.Frame(self.window, padding=(12, 4))
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(footer, textvariable=self.status_var).pack(side="left")

    # --------------------------------------------------
    # PROJECT SELECTION
    # --------------------------------------------------

    def _on_project_selected(self, _event=None):
        project = self._project()
        if project:
            self.selected_project = project
            self._select_project()

    def _select_project(self):
        project = self._project()
        if not project:
            return

        self.selected_project = project
        self.project_title.config(text=project["name"])
        self.selected_container = None
        self._clear_containers()
        self._refresh()

    def _clear_containers(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _on_container_selected(self, _event=None):
        selection = self.tree.selection()
        self.selected_container = selection[0] if selection else None

    # --------------------------------------------------
    # ASYNC COMMAND EXECUTION
    # --------------------------------------------------

    def _compose(self, project, *args, timeout=None):
        compose_file = Path(project["compose_file"])
        if not compose_file.is_file():
            raise FileNotFoundError(f"Compose file not found: {compose_file}")

        command = [
            "docker", "compose",
            "-f", str(compose_file),
            *args,
        ]

        result = subprocess.run(
            command,
            cwd=str(compose_file.parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout or self.COMMAND_TIMEOUT,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0
            ),
        )

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip() or result.stdout.strip()
                or f"Docker command failed: {result.returncode}"
            )

        return result.stdout.strip()

    def _start_job(self, label, callback):
        if self.busy:
            self._set_status("Another Docker operation is in progress.")
            return

        if not self._project():
            self._set_status("Select a Compose project first.")
            return

        self.busy = True
        self._set_status(f"{label}...")

        for button in (
            self.start_button, self.stop_button, self.restart_button
        ):
            button.state(["disabled"])

        project = self._project()

        def worker():
            try:
                result = callback(project)
                self.events.put(("job_done", label, result, None))
            except Exception as error:
                self.events.put(("job_done", label, None, str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def _run_compose(self, action):
        commands = {
            "up": ("Starting", ("up", "-d")),
            "stop": ("Stopping", ("stop",)),
            "restart": ("Restarting", ("restart",)),
        }

        label, args = commands[action]

        def run(project):
            return self._compose(project, *args)

        self._start_job(label, run)

    def _refresh(self):
        if self.busy:
            return

        project = self._project()
        if not project:
            return

        self.busy = True

        def worker():
            try:
                docker_version = subprocess.run(
                    ["docker", "version", "--format", "{{.Server.Version}}"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                        else 0
                    ),
                )

                if docker_version.returncode != 0:
                    raise RuntimeError(
                        docker_version.stderr.strip()
                        or "Docker Engine is not available."
                    )

                raw = self._compose(project, "ps", "-a", "-q", timeout=15)
                container_ids = list(dict.fromkeys(raw.splitlines()))

                if container_ids:
                    inspected = subprocess.run(
                        ["docker", "inspect", *container_ids],
                        capture_output=True,
                        text=True,
                        timeout=15,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=(
                            subprocess.CREATE_NO_WINDOW
                            if hasattr(subprocess, "CREATE_NO_WINDOW")
                            else 0
                        ),
                    )
                    if inspected.returncode != 0:
                        raise RuntimeError(inspected.stderr.strip())
                    containers = json.loads(inspected.stdout)
                else:
                    containers = []

                self.events.put((
                    "refresh_done", project, containers,
                    docker_version.stdout.strip(), None,
                ))
            except Exception as error:
                self.events.put((
                    "refresh_done", project, [], "", str(error),
                ))
            finally:
                self.events.put(("refresh_unlock",))

        threading.Thread(target=worker, daemon=True).start()

    def _process_events(self):
        if self.closed:
            return

        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]

                if kind == "job_done":
                    _, label, output, error = event
                    self.busy = False
                    self._set_buttons_enabled()

                    if error:
                        self._set_status(f"{label} failed: {error}")
                        messagebox.showerror(
                            "Docker Manager", error, parent=self.window
                        )
                    else:
                        self._set_status(f"{label} completed.")
                        self._refresh()

                elif kind == "refresh_done":
                    _, project, containers, version, error = event

                    if project != self.selected_project:
                        continue

                    if error:
                        self.connection_label.config(text="Docker unavailable")
                        self._set_status(error)
                        self.app_status.config(text="Application: unavailable")
                        continue

                    self.connection_label.config(
                        text=f"Docker Engine {version}"
                    )
                    self._render_containers(containers)
                    self._check_application(project)
                    self.last_refresh = time.monotonic()
                    self.elapsed_label.config(
                        text="Last refresh: just now"
                    )

                elif kind == "refresh_unlock":
                    self.busy = False
                    self._set_buttons_enabled()
                
                elif kind == "app_done":
                    _, project, result = event
                    if project == self.selected_project:
                        self.app_status.config(
                            text=f"Application: {result}"
                        )
                        
                elif kind == "app_probe_unlock":
                    self._http_probe_running = False

                elif kind == "logs_done":
                    _, output_window, logs = event
                    if output_window.winfo_exists():
                        for widget in output_window.winfo_children():
                            if isinstance(widget, tk.Text):
                                widget.configure(state="normal")
                                widget.delete("1.0", "end")
                                widget.insert("1.0", logs)
                                widget.configure(state="disabled")
                                break


        except queue.Empty:
            pass

        self.window.after(150, self._process_events)

    def _set_buttons_enabled(self):
        for button in (
            self.start_button, self.stop_button, self.restart_button
        ):
            button.state(["!disabled"])

    def _schedule_refresh(self):
        if self.closed:
            return

        if not self.busy and self._project():
            self._refresh()

        self.window.after(self.POLL_INTERVAL, self._schedule_refresh)

    # --------------------------------------------------
    # CONTAINER STATUS
    # --------------------------------------------------

    @staticmethod
    def _format_started(value):
        if not value or value.startswith("0001-01-01"):
            return "—"

        try:
            from datetime import datetime
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return value

    def _render_containers(self, containers):
        previous = self.selected_container
        self._clear_containers()

        for container in containers:
            state = container.get("State", {})
            state_name = state.get("Status", "unknown")
            health = state.get("Health", {}).get("Status", "not configured")
            name = container.get("Name", "").lstrip("/")
            exit_code = state.get("ExitCode", "")
            started = self._format_started(state.get("StartedAt"))

            if state_name == "running" and health in (
                "healthy", "not configured"
            ):
                tag = "healthy"
            elif state_name in ("exited", "dead") or health == "unhealthy":
                tag = "error"
            else:
                tag = "warning"

            self.tree.insert(
                "",
                "end",
                iid=container.get("Id", name),
                text=name,
                values=(state_name, health, started, exit_code),
                tags=(tag,),
            )

        if previous and self.tree.exists(previous):
            self.tree.selection_set(previous)
            self.selected_container = previous
        else:
            self.selected_container = None

        if not containers:
            self._set_status(
                "No containers found. The project may not have been started."
            )
        else:
            self._set_status(f"Containers found: {len(containers)}")

    # --------------------------------------------------
    # APPLICATION READINESS
    # --------------------------------------------------

    def _check_application(self, project):
        url = project.get("url", "").strip()

        if not url:
            self.app_status.config(
                text="Application: add a URL in project settings to check HTTP."
            )
            return

        self.app_status.config(text=f"Application: checking {url} ...")

        def worker():
            started = time.monotonic()
            try:
                request = urllib.request.Request(
                    url, headers={"User-Agent": "Toolkit-Docker-Manager"}
                )
                with urllib.request.urlopen(request, timeout=4) as response:
                    result = (
                        f"HTTP {response.status} · "
                        f"{time.monotonic() - started:.1f}s"
                    )
            except urllib.error.HTTPError as error:
                result = f"HTTP {error.code} · endpoint responded"
            except Exception as error:
                result = f"Not ready · {type(error).__name__}: {error}"

            self.events.put(("app_done", project, result))

        # Prevent concurrent HTTP probes for the same project.
        if getattr(self, "_http_probe_running", False):
            return

        self._http_probe_running = True

        def guarded_worker():
            try:
                worker()
            finally:
                self.events.put(("app_probe_unlock",))

        threading.Thread(target=guarded_worker, daemon=True).start()

    # --------------------------------------------------
    # LOGS / BROWSER
    # --------------------------------------------------

    def _show_logs(self):
        container_id = self.selected_container
        project = self._project()

        if not project or not container_id:
            messagebox.showinfo(
                "Docker Manager",
                "Select a container first.",
                parent=self.window,
            )
            return

        output_window = tk.Toplevel(self.window)
        output_window.title("Container logs")
        output_window.geometry("850x550")

        text_widget = tk.Text(
            output_window, wrap="none", font=("Consolas", 9)
        )
        text_widget.pack(fill="both", expand=True)

        text_widget.insert("1.0", "Loading logs...")
        text_widget.configure(state="disabled")

        def worker():
            try:
                result = subprocess.run(
                    ["docker", "logs", "--tail", "300", container_id],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                        else 0
                    ),
                )
                logs = result.stdout + (
                    "\n" + result.stderr if result.stderr else ""
                )
                if result.returncode:
                    raise RuntimeError(logs.strip() or "Unable to read logs.")
                self.events.put(("logs_done", output_window, logs))
            except Exception as error:
                self.events.put(("logs_done", output_window, str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def _open_web_ui(self):
        import webbrowser

        project = self._project()
        if not project:
            return

        url = project.get("url", "").strip()
        if not url:
            messagebox.showinfo(
                "Docker Manager",
                "Set the web interface URL in project settings first.",
                parent=self.window,
            )
            return

        webbrowser.open(url)

    # --------------------------------------------------
    # STATUS / CLEANUP
    # --------------------------------------------------

    def _set_status(self, text):
        self.status_var.set(text)

    def _close(self):
        self.closed = True
        self.window.destroy()


def open_docker_manager(root, base_dir, settings=None):
    DockerManagerWindow(root, base_dir, settings)
    