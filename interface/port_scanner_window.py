from __future__ import annotations

import csv
import queue
import time
import tkinter as tk

from datetime import datetime
from tkinter import ttk, filedialog, messagebox

from scripts.port_scanner import (
    MAX_HOSTS,
    MAX_PROBES,
    MAX_WORKERS,
    Scanner,
    check_scope,
    has_public,
    local_network,
    parse_ports,
    parse_targets,
    preset_ports,
)


PRESETS = [
    "Common ports (~80)",
    "Well-known 1-1024",
    "All ports 1-65535",
    "Custom",
]

POLL_MS = 150
ROWS_PER_TICK = 500


class PortScannerWindow:
    """Сканер открытых TCP-портов для Toolkit."""

    def __init__(self, root, base_dir=None, settings=None):
        self.root = root
        self.settings = settings or {}

        self.scanner = None
        self.closed = False
        self.found = 0
        self.found_hosts = set()
        self._scan_info = ""

        self.window = tk.Toplevel(root)
        self.window.title("Port Scanner")
        self.window.geometry("900x620")
        self.window.minsize(720, 480)
        self.window.protocol("WM_DELETE_WINDOW", self._close)

        self._build_ui()
        self._poll()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def _build_ui(self):
        win = self.window
        win.columnconfigure(0, weight=1)
        win.rowconfigure(2, weight=1)

        ttk.Label(
            win, text="PORT SCANNER", font=("Arial", 15, "bold")
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        form = ttk.LabelFrame(win, text="Scan settings", padding=10)
        form.grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 8))
        form.columnconfigure(1, weight=1)

        # target
        ttk.Label(form, text="Target").grid(row=0, column=0, sticky="w")

        self.target_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(form, textvariable=self.target_var).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        ttk.Button(
            form, text="My network",
            command=lambda: self.target_var.set(local_network()),
        ).grid(row=0, column=2)

        ttk.Label(
            form,
            foreground="#666666",
            text="Host, name, 192.168.1.0/24, 192.168.1.10-50. "
                 "Separate several targets with commas.",
        ).grid(row=1, column=1, columnspan=2, sticky="w", padx=8)

        # ports
        ttk.Label(form, text="Ports").grid(row=2, column=0, sticky="w", pady=(8, 0))

        ports_row = ttk.Frame(form)
        ports_row.grid(row=2, column=1, columnspan=2, sticky="ew", padx=8, pady=(8, 0))
        ports_row.columnconfigure(1, weight=1)

        self.preset_var = tk.StringVar(value=PRESETS[0])
        preset = ttk.Combobox(
            ports_row, textvariable=self.preset_var,
            values=PRESETS, state="readonly", width=22,
        )
        preset.grid(row=0, column=0)
        preset.bind("<<ComboboxSelected>>", self._on_preset)

        self.ports_var = tk.StringVar(value="22,80,443,5432,8080,8000-8100")
        self.ports_entry = ttk.Entry(
            ports_row, textvariable=self.ports_var, state="disabled"
        )
        self.ports_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        # options
        options = ttk.Frame(form)
        options.grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))

        ttk.Label(options, text="Timeout, s").pack(side="left")
        self.timeout_var = tk.StringVar(value="0.5")
        ttk.Spinbox(
            options, textvariable=self.timeout_var,
            from_=0.1, to=5.0, increment=0.1, width=5, format="%.1f",
        ).pack(side="left", padx=(4, 14))

        ttk.Label(options, text="Threads").pack(side="left")
        self.workers_var = tk.StringVar(value="200")
        ttk.Spinbox(
            options, textvariable=self.workers_var,
            from_=10, to=MAX_WORKERS, increment=10, width=5,
        ).pack(side="left", padx=(4, 14))

        self.banner_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options, text="Read banners", variable=self.banner_var
        ).pack(side="left", padx=(0, 14))

        self.public_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options,
            text="Allow a public address (only hosts you own or may test)",
            variable=self.public_var,
        ).pack(side="left")

        # results
        box = ttk.Frame(win)
        box.grid(row=2, column=0, sticky="nsew", padx=12)
        box.columnconfigure(0, weight=1)
        box.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            box, columns=("host", "port", "service", "banner"),
            show="headings", selectmode="browse",
        )
        for column, title, width in (
            ("host", "Host", 150),
            ("port", "Port", 70),
            ("service", "Service", 190),
            ("banner", "Banner", 400),
        ):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, anchor="w")
        self.tree.column("port", anchor="center")

        ybar = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ybar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")

        # controls
        bottom = ttk.Frame(win, padding=(12, 8))
        bottom.grid(row=3, column=0, sticky="ew")
        bottom.columnconfigure(3, weight=1)

        self.start_button = ttk.Button(bottom, text="▶ Start", command=self._start)
        self.start_button.grid(row=0, column=0)

        self.stop_button = ttk.Button(
            bottom, text="■ Stop", command=self._stop, state="disabled"
        )
        self.stop_button.grid(row=0, column=1, padx=6)

        ttk.Button(
            bottom, text="Export CSV", command=self._export
        ).grid(row=0, column=2)

        self.progress = ttk.Progressbar(bottom, maximum=100)
        self.progress.grid(row=0, column=3, sticky="ew", padx=(14, 0))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(win, textvariable=self.status_var).grid(
            row=4, column=0, sticky="w", padx=12, pady=(0, 8)
        )

    def _on_preset(self, _event=None):
        custom = self.preset_var.get() == "Custom"
        self.ports_entry.config(state="normal" if custom else "disabled")

    # --------------------------------------------------
    # INPUT
    # --------------------------------------------------

    def _ports(self):
        if self.preset_var.get() == "Custom":
            return parse_ports(self.ports_var.get())
        return preset_ports(self.preset_var.get())

    def _options(self):
        try:
            timeout = float(self.timeout_var.get().replace(",", "."))
        except ValueError:
            raise ValueError("Timeout must be a number of seconds.") from None

        if not 0.05 <= timeout <= 10:
            raise ValueError("Timeout must be between 0.05 and 10 seconds.")

        try:
            workers = int(self.workers_var.get())
        except ValueError:
            raise ValueError("Threads must be a whole number.") from None

        if not 1 <= workers <= MAX_WORKERS:
            raise ValueError(f"Threads must be between 1 and {MAX_WORKERS}.")

        return timeout, workers

    # --------------------------------------------------
    # SCAN CONTROL
    # --------------------------------------------------

    def _running(self):
        return self.scanner is not None

    def _start(self):
        if self._running():
            return

        try:
            hosts = parse_targets(self.target_var.get())
            ports = self._ports()
            timeout, workers = self._options()
        except ValueError as error:
            messagebox.showwarning("Port Scanner", str(error), parent=self.window)
            return

        error = check_scope(hosts, self.public_var.get())
        if error:
            messagebox.showwarning("Port Scanner", error, parent=self.window)
            return

        if has_public(hosts) and not messagebox.askyesno(
            "Port Scanner",
            f"{hosts[0]} is a public address.\n\n"
            "Scan only systems you own or have explicit permission to test. "
            "Unauthorized scanning can be illegal and may violate "
            "your company's policy.\n\nContinue?",
            icon="warning",
            parent=self.window,
        ):
            return

        total = len(hosts) * len(ports)

        if total > MAX_PROBES:
            messagebox.showwarning(
                "Port Scanner",
                f"Too many probes: {len(hosts)} hosts x {len(ports)} ports = "
                f"{total:,}.\nThe limit is {MAX_PROBES:,}. "
                "Narrow the network or the port list.",
                parent=self.window,
            )
            return

        worst_case = total / workers * timeout
        if worst_case > 120 and not messagebox.askyesno(
            "Port Scanner",
            f"{len(hosts)} hosts x {len(ports)} ports = {total:,} probes.\n"
            f"If most ports do not answer this can take up to "
            f"~{worst_case / 60:.0f} minutes.\n\nStart anyway?",
            parent=self.window,
        ):
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.found = 0
        self.found_hosts = set()
        self._scan_info = f"{len(hosts)} hosts x {len(ports)} ports"
        self.progress["value"] = 0

        self.scanner = Scanner(
            hosts, ports, timeout=timeout, workers=workers,
            banners=self.banner_var.get(),
        )
        self.scanner.start()

        self.start_button.state(["disabled"])
        self.stop_button.state(["!disabled"])
        self.status_var.set(f"Scanning {self._scan_info}...")

    def _stop(self):
        if self.scanner:
            self.scanner.stop()
            self.status_var.set("Stopping...")

    def _finish(self):
        scanner = self.scanner
        self.scanner = None

        self.start_button.state(["!disabled"])
        self.stop_button.state(["disabled"])

        percent = 100 * scanner.done / scanner.total if scanner.total else 100
        self.progress["value"] = percent

        state = "Stopped" if scanner.stopped and scanner.done < scanner.total else "Done"

        self.status_var.set(
            f"{state}: {self._scan_info} in {scanner.elapsed:.1f} s · "
            f"open ports: {self.found} on {len(self.found_hosts)} host(s)"
        )

    def _poll(self):
        if self.closed:
            return

        scanner = self.scanner

        if scanner:
            for _ in range(ROWS_PER_TICK):
                try:
                    host, port, service, banner = scanner.results.get_nowait()
                except queue.Empty:
                    break

                self.tree.insert(
                    "", "end", values=(host, port, service, banner)
                )
                self.found += 1
                self.found_hosts.add(host)

            if scanner.finished.is_set() and scanner.results.empty():
                self._finish()
            elif not scanner.stopped:
                percent = 100 * scanner.done / scanner.total if scanner.total else 100
                elapsed = time.monotonic() - scanner.started_at
                self.progress["value"] = percent
                self.status_var.set(
                    f"Scanning {self._scan_info}... "
                    f"{scanner.done:,}/{scanner.total:,} ({percent:.0f}%) · "
                    f"open: {self.found} · {elapsed:.0f} s"
                )

        try:
            self.window.after(POLL_MS, self._poll)
        except tk.TclError:
            pass

    # --------------------------------------------------
    # EXPORT / CLOSE
    # --------------------------------------------------

    def _export(self):
        rows = [self.tree.item(i, "values") for i in self.tree.get_children()]

        if not rows:
            messagebox.showinfo(
                "Port Scanner", "There are no results to export.",
                parent=self.window,
            )
            return

        filename = filedialog.asksaveasfilename(
            parent=self.window,
            title="Export results",
            defaultextension=".csv",
            initialfile=f"scan_{datetime.now():%Y%m%d_%H%M%S}.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return

        try:
            # utf-8-sig, чтобы Excel правильно открыл файл
            with open(filename, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(["host", "port", "service", "banner"])
                writer.writerows(rows)
        except OSError as error:
            messagebox.showerror("Port Scanner", str(error), parent=self.window)
            return

        self.status_var.set(f"Saved: {filename}")

    def _close(self):
        self.closed = True

        if self.scanner:
            self.scanner.stop()

        self.window.destroy()


_instance = None


def open_port_scanner(root, base_dir=None, settings=None):
    """Одно окно на программу: повторный вызов выводит его вперёд."""
    global _instance

    if _instance is not None and not _instance.closed:
        try:
            _instance.window.deiconify()
            _instance.window.lift()
            _instance.window.focus_force()
            return _instance
        except tk.TclError:
            pass

    _instance = PortScannerWindow(root, base_dir, settings)
    return _instance
