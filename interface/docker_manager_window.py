from __future__ import annotations

import json
import queue
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
import webbrowser

import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk, filedialog, messagebox


NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

DOCKER_MISSING = (
    "Docker CLI not found. Install Docker Desktop and make sure "
    "'docker' is available in PATH."
)


# --------------------------------------------------
# HELPERS (no Tk, easy to test)
# --------------------------------------------------

def _run(command, timeout, cwd=None, merge_stderr=False):
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=NO_WINDOW,
        )
    except FileNotFoundError:
        raise RuntimeError(DOCKER_MISSING) from None
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"Timed out after {timeout} s: {' '.join(command[:4])}"
        ) from None


_TIME_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
)


def parse_docker_time(value):
    if not value or str(value).startswith("0001-01-01"):
        return None

    match = _TIME_RE.match(str(value))
    if not match:
        return None

    base, fraction, tz = match.groups()
    fraction = ((fraction or ".") + "000000")[:7]
    tz = "+00:00" if tz in (None, "Z") else tz

    try:
        return datetime.fromisoformat(f"{base}{fraction}{tz}")
    except ValueError:
        return None


def format_duration(seconds):
    seconds = max(int(seconds), 0)
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)

    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def describe_container(container, now=None):
    state = container.get("State") or {}
    labels = (container.get("Config") or {}).get("Labels") or {}

    name = (container.get("Name") or "").lstrip("/")
    service = labels.get("com.docker.compose.service") or name
    status = state.get("Status", "unknown")
    health = (state.get("Health") or {}).get("Status", "not configured")
    exit_code = state.get("ExitCode", 0)

    uptime = "—"
    if status == "running":
        started = parse_docker_time(state.get("StartedAt"))
        if started:
            now = now or datetime.now(timezone.utc)
            uptime = format_duration((now - started).total_seconds())

    if status == "running" and health in ("healthy", "not configured"):
        tag = "healthy"
    elif status == "exited" and exit_code == 0:
        tag = "done"
    elif status in ("exited", "dead") or health == "unhealthy":
        tag = "error"
    else:
        tag = "warning"

    return {
        "id": container.get("Id") or name,
        "service": service,
        "name": name,
        "state": status,
        "health": health,
        "uptime": uptime,
        "exit_code": "" if status == "running" else exit_code,
        "tag": tag,
    }


def _short(text, limit=200):
    lines = [line for line in str(text).splitlines() if line.strip()]
    first = lines[0].strip() if lines else str(text)
    return first if len(first) <= limit else first[: limit - 1] + "…"


def _grab(window):
    try:
        window.wait_visibility()
        window.grab_set()
    except tk.TclError:
        pass


# --------------------------------------------------
# WINDOW
# --------------------------------------------------

class DockerManagerWindow:
    """Docker Compose manager for Toolkit."""

    POLL_INTERVAL = 3000
    COMMAND_TIMEOUT = 120
    ENGINE_CHECK_INTERVAL = 30

    def __init__(self, root, base_dir, settings=None):
        self.root = root
        self.base_dir = Path(base_dir)
        self.settings = settings or {}

        self.db_path = self.base_dir / "db" / "docker_projects.json"
        self.projects = self._load_projects()
        self.selected_project = None
        self.selected_container = None

        self.events = queue.Queue()
        self.job_busy = False
        self.refresh_busy = False
        self.closed = False
        self.last_refresh = 0.0

        self._engine_version = ""
        self._engine_checked = 0.0
        self._probing = set()
        self._app_known = False

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
        except (OSError, ValueError):
            return []

        if not isinstance(data, list):
            return []

        projects = []
        for item in data:
            if (
                isinstance(item, dict)
                and item.get("compose_file")
                and item.get("name")
            ):
                item.setdefault("url", "")
                projects.append(item)

        return projects

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
            messagebox.showerror(
                "Docker Manager", "File not found.", parent=self.window
            )
            return

        existing = next(
            (p for p in self.projects
             if Path(p["compose_file"]) == compose_file),
            None,
        )

        if existing:
            messagebox.showinfo(
                "Docker Manager", "Project already added.", parent=self.window
            )
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
        self.project_list.selection_clear(0, tk.END)
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
        self.selected_container = None
        self._refresh_project_list()
        self._clear_containers()
        self.project_title.config(text="Select a project")
        self._set_status("Project removed from Toolkit.")

    def _edit_project(self):
        project = self._project()
        if not project:
            return

        dialog = tk.Toplevel(self.window)
        dialog.title("Project settings")
        dialog.geometry("520x190")
        dialog.transient(self.window)

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

        _grab(dialog)

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
            self.project_list.selection_set(self.projects.index(current))

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

        self.connection_label = ttk.Label(header, text="Checking Docker...")
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
            actions, text="↻ Restart",
            command=lambda: self._run_compose("restart"),
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
        self.tree.heading("#0", text="Service")
        self.tree.heading("state", text="State")
        self.tree.heading("health", text="Health")
        self.tree.heading("uptime", text="Uptime")
        self.tree.heading("exit", text="Exit code")

        self.tree.column("#0", width=220, minwidth=140)
        self.tree.column("state", width=105, anchor="center")
        self.tree.column("health", width=110, anchor="center")
        self.tree.column("uptime", width=120, anchor="center")
        self.tree.column("exit", width=80, anchor="center")

        self.tree.grid(row=2, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_container_selected)

        self.tree.tag_configure("healthy", foreground="#16803c")
        self.tree.tag_configure("warning", foreground="#b7791f")
        self.tree.tag_configure("error", foreground="#c53030")
        self.tree.tag_configure("done", foreground="#718096")

        details = ttk.LabelFrame(main, text="Diagnostics", padding=8)
        details.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        details.columnconfigure(0, weight=1)

        self.app_status = ttk.Label(details, text="Application: not checked")
        self.app_status.grid(row=0, column=0, sticky="w")

        self.elapsed_label = ttk.Label(details, text="Last refresh: —")
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
        if self._project():
            self._select_project()

    def _select_project(self):
        project = self._project()
        if not project:
            return

        self.selected_project = project
        self.project_title.config(text=project["name"])
        self.selected_container = None
        self._app_known = False
        self.app_status.config(text="Application: not checked")
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

        result = _run(
            ["docker", "compose", "-f", str(compose_file), *args],
            timeout=timeout or self.COMMAND_TIMEOUT,
            cwd=str(compose_file.parent),
        )

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip()
                or result.stdout.strip()
                or f"Docker command failed: {result.returncode}"
            )

        return result.stdout.strip()

    def _engine_version_cached(self):
        now = time.monotonic()

        if (
            self._engine_version
            and now - self._engine_checked < self.ENGINE_CHECK_INTERVAL
        ):
            return self._engine_version

        result = _run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            timeout=8,
        )
        version = result.stdout.strip()

        if result.returncode != 0 or not version:
            raise RuntimeError(
                result.stderr.strip()
                or "Docker Engine is not available. Is Docker Desktop running?"
            )

        self._engine_version = version
        self._engine_checked = now
        return version

    def _start_job(self, label, callback):
        if self.job_busy:
            self._set_status("Another Docker operation is in progress.")
            return

        project = self._project()
        if not project:
            self._set_status("Select a Compose project first.")
            return

        self.job_busy = True
        self._set_status(f"{label}...")
        self._set_buttons_enabled()

        def worker():
            try:
                result = callback(project)
                self.events.put(("job_done", label, result, None))
            except Exception as error:
                self.events.put(("job_done", label, None, str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def _run_compose(self, action):
        commands = {
            "up": ("Starting", ("up", "-d"), 1800),
            "stop": ("Stopping", ("stop",), 300),
            "restart": ("Restarting", ("restart",), 300),
        }

        label, args, timeout = commands[action]

        def run(project):
            return self._compose(project, *args, timeout=timeout)

        self._start_job(label, run)

    def _refresh(self):
        if self.refresh_busy:
            return

        project = self._project()
        if not project:
            return

        self.refresh_busy = True

        def worker():
            try:
                version = self._engine_version_cached()

                raw = self._compose(project, "ps", "-a", "-q", timeout=15)
                ids = list(dict.fromkeys(
                    line.strip() for line in raw.splitlines() if line.strip()
                ))

                containers = []
                if ids:
                    inspected = _run(["docker", "inspect", *ids], timeout=15)
                    if inspected.returncode != 0:
                        raise RuntimeError(
                            inspected.stderr.strip() or "docker inspect failed"
                        )
                    containers = json.loads(inspected.stdout)

                self.events.put(
                    ("refresh_done", project, containers, version, None)
                )
            except Exception as error:
                self._engine_version = ""
                self._engine_checked = 0.0
                self.events.put(("refresh_done", project, [], "", str(error)))
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
                    _, label, _output, error = event
                    self.job_busy = False
                    self._set_buttons_enabled()

                    if error:
                        self._set_status(f"{label} failed: {_short(error)}")
                        messagebox.showerror(
                            "Docker Manager", error, parent=self.window
                        )
                    else:
                        self._set_status(f"{label} completed.")
                        self._refresh()

                elif kind == "refresh_done":
                    _, project, containers, version, error = event

                    if project is not self.selected_project:
                        continue

                    if error:
                        self.connection_label.config(text="Docker unavailable")
                        self._clear_containers()
                        self.selected_container = None
                        self._set_status(_short(error))
                        self.app_status.config(text="Application: unavailable")
                        continue

                    self.connection_label.config(
                        text=f"Docker Engine {version}"
                    )
                    self._render_containers(containers)

                    running = sum(
                        1 for c in containers
                        if (c.get("State") or {}).get("Status") == "running"
                    )
                    self._check_application(project, running)

                    self.last_refresh = time.monotonic()
                    self.elapsed_label.config(
                        text=f"Last refresh: {time.strftime('%H:%M:%S')}"
                    )

                elif kind == "refresh_unlock":
                    self.refresh_busy = False

                elif kind == "app_done":
                    _, project, result = event
                    if project is self.selected_project:
                        self._app_known = True
                        self.app_status.config(
                            text=f"Application: {result}  "
                                 f"(checked {time.strftime('%H:%M:%S')})"
                        )

                elif kind == "app_probe_unlock":
                    self._probing.discard(event[1])

                elif kind == "call":
                    event[1]()

        except queue.Empty:
            pass

        try:
            self.window.after(150, self._process_events)
        except tk.TclError:
            pass

    def _set_buttons_enabled(self):
        state = ["disabled"] if self.job_busy else ["!disabled"]

        for button in (
            self.start_button, self.stop_button, self.restart_button
        ):
            button.state(state)

    def _schedule_refresh(self):
        if self.closed:
            return

        if self._project():
            self._refresh()

        try:
            self.window.after(self.POLL_INTERVAL, self._schedule_refresh)
        except tk.TclError:
            pass

    # --------------------------------------------------
    # CONTAINER STATUS
    # --------------------------------------------------

    def _render_containers(self, containers):
        rows = sorted(
            (describe_container(c) for c in containers),
            key=lambda row: row["service"],
        )

        wanted = {row["id"] for row in rows}

        for stale in set(self.tree.get_children()) - wanted:
            self.tree.delete(stale)

        for index, row in enumerate(rows):
            values = (
                row["state"], row["health"], row["uptime"], row["exit_code"]
            )

            if self.tree.exists(row["id"]):
                self.tree.item(
                    row["id"], text=row["service"],
                    values=values, tags=(row["tag"],),
                )
                self.tree.move(row["id"], "", index)
            else:
                self.tree.insert(
                    "", index, iid=row["id"], text=row["service"],
                    values=values, tags=(row["tag"],),
                )

        if self.selected_container and not self.tree.exists(
            self.selected_container
        ):
            self.selected_container = None

        if not rows:
            self._set_status(
                "No containers found. The project may not have been started."
            )
            return

        running = sum(1 for row in rows if row["state"] == "running")
        problems = sum(1 for row in rows if row["tag"] == "error")

        text = f"Containers: {len(rows)} · running: {running}"
        if problems:
            text += f" · problems: {problems}"
        self._set_status(text)

    # --------------------------------------------------
    # APPLICATION READINESS
    # --------------------------------------------------

    def _check_application(self, project, running):
        url = project.get("url", "").strip()

        if not url:
            self.app_status.config(
                text="Application: add a URL in project settings to check HTTP."
            )
            return

        if not running:
            self._app_known = False
            self.app_status.config(
                text="Application: containers are not running."
            )
            return

        key = project["compose_file"]

        if key in self._probing:
            return

        self._probing.add(key)
        
        if not self._app_known:
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
            finally:
                self.events.put(("app_probe_unlock", key))

            self.events.put(("app_done", project, result))

        threading.Thread(target=worker, daemon=True).start()

    # --------------------------------------------------
    # LOGS / BROWSER
    # --------------------------------------------------

    @staticmethod
    def _set_text(widget, content):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def _show_logs(self):
        container_id = self.selected_container

        if (
            not self._project()
            or not container_id
            or not self.tree.exists(container_id)
        ):
            messagebox.showinfo(
                "Docker Manager",
                "Select a container first.",
                parent=self.window,
            )
            return

        title = self.tree.item(container_id, "text")

        win = tk.Toplevel(self.window)
        win.title(f"Logs — {title}")
        win.geometry("900x560")

        top = ttk.Frame(win, padding=(8, 6))
        top.pack(fill="x")

        body = ttk.Frame(win)
        body.pack(fill="both", expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        text = tk.Text(
            body, wrap="none", font=("Consolas", 9), state="disabled"
        )
        ybar = ttk.Scrollbar(body, orient="vertical", command=text.yview)
        xbar = ttk.Scrollbar(body, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)

        text.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")

        loading = {"on": False}

        def finish(logs):
            loading["on"] = False
            if not text.winfo_exists():
                return
            self._set_text(text, logs)
            text.see("end")      # the most fresh rows below

        def load():
            if loading["on"]:
                return
            loading["on"] = True
            self._set_text(text, "Loading logs...")

            def worker():
                try:
                    result = _run(
                        ["docker", "logs", "--tail", "300", container_id],
                        timeout=15,
                        merge_stderr=True,   # stdout & stderr
                    )
                    logs = result.stdout
                    if result.returncode:
                        logs = logs.strip() or "Unable to read logs."
                    elif not logs.strip():
                        logs = "(no log output)"
                except Exception as error:
                    logs = str(error)

                self.events.put(("call", lambda: finish(logs)))

            threading.Thread(target=worker, daemon=True).start()

        ttk.Button(top, text="Refresh", command=load).pack(side="left")
        ttk.Label(top, text="last 300 lines").pack(side="left", padx=8)

        load()

    def _open_web_ui(self):
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


_instance = None


def open_docker_manager(root, base_dir, settings=None):
    global _instance

    if _instance is not None and not _instance.closed:
        try:
            _instance.window.deiconify()
            _instance.window.lift()
            _instance.window.focus_force()
            return _instance
        except tk.TclError:
            pass

    _instance = DockerManagerWindow(root, base_dir, settings)
    return _instance