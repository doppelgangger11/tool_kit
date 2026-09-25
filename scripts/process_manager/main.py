"""
Port Manager - сканер занятых портов с возможностью завершать процессы,
при необходимости запрашивая права администратора (UAC).

Запуск: python -m ui.main  (из корня localhost_manager/)

Логика завершения процесса:
1. Сначала пробуем обычный taskkill без повышения прав - для процессов
   пользователя этого обычно достаточно.
2. Если ОС отвечает отказом (Access Denied - часто бывает с системными
   процессами или процессами, запущенными от имени другого пользователя),
   автоматически всплывает стандартный Windows UAC-диалог с запросом
   повышения прав именно на эту операцию.

Без прав администратора psutil также может не видеть часть соединений
чужих процессов - поэтому в шапке окна показывается баннер с кнопкой
"Перезапустить от администратора", если приложение сейчас запущено
без elevation.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin_utils import is_admin, relaunch_as_admin, kill_pid_elevated, kill_pid_plain
from port_scanner import list_all_listening_ports


SCAN_INTERVAL_MS = 2000


class PortManagerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Port Manager")
        self.root.geometry("800x480")

        self._build_ui()
        self._refresh_now()
        self.root.after(SCAN_INTERVAL_MS, self._refresh_loop)

    # ---------- UI ----------

    def _build_ui(self) -> None:
        if not is_admin():
            banner = ttk.Frame(self.root, style="Warn.TFrame")
            banner.pack(side="top", fill="x")
            style = ttk.Style()
            style.configure("Warn.TFrame", background="#553c00")
            label = tk.Label(
                banner,
                text="⚠ Запущено без прав администратора: часть портов/процессов может быть не видна, "
                     "а завершение некоторых процессов запросит UAC отдельно.",
                bg="#553c00", fg="white", anchor="w", padx=8, pady=4,
            )
            label.pack(side="left", fill="x", expand=True)
            ttk.Button(banner, text="Перезапустить от администратора",
                       command=self._relaunch_as_admin).pack(side="right", padx=6, pady=4)

        toolbar = ttk.Frame(self.root)
        toolbar.pack(side="top", fill="x", padx=6, pady=6)
        ttk.Button(toolbar, text="Обновить сейчас", command=self._refresh_now).pack(side="left")
        ttk.Button(toolbar, text="Завершить процесс", command=self._kill_selected).pack(side="left", padx=4)
        ttk.Label(toolbar, text="  Автообновление каждые 2 сек.").pack(side="left")

        columns = ("pid", "process", "proto", "cmdline")
        self.tree = ttk.Treeview(self.root, columns=columns, show="tree headings")
        self.tree.heading("#0", text="Порт")
        self.tree.heading("pid", text="PID")
        self.tree.heading("process", text="Процесс")
        self.tree.heading("proto", text="Протокол")
        self.tree.heading("cmdline", text="Командная строка")
        self.tree.column("#0", width=90, anchor="center")
        self.tree.column("pid", width=80, anchor="center")
        self.tree.column("process", width=150)
        self.tree.column("proto", width=80, anchor="center")
        self.tree.column("cmdline", width=420)
        self.tree.pack(side="top", fill="both", expand=True, padx=6, pady=(0, 6))
        # завершение по двойному клику - для скорости
        self.tree.bind("<Double-1>", lambda e: self._kill_selected())

        self.status_bar = ttk.Label(self.root, text="Готово", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")

    # ---------- сканирование ----------

    def _refresh_loop(self) -> None:
        self._refresh_now()
        self.root.after(SCAN_INTERVAL_MS, self._refresh_loop)

    def _refresh_now(self) -> None:
        selected = self.tree.selection()
        selected_key = selected[0] if selected else None

        ports = list_all_listening_ports()
        self.tree.delete(*self.tree.get_children())
        for item in ports:
            proto = "IPv6" if item.is_ipv6 else "IPv4"
            key = f"{item.port}-{item.pid}-{proto}"
            self.tree.insert(
                "", "end", iid=key, text=str(item.port),
                values=(item.pid, item.process_name, proto, item.cmdline),
            )

        if selected_key and self.tree.exists(selected_key):
            self.tree.selection_set(selected_key)

        self.status_bar.config(text=f"Найдено занятых портов: {len(ports)}")

    # ---------- завершение процессов ----------

    def _kill_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return

        pid_str = self.tree.set(sel[0], "pid")
        port = self.tree.item(sel[0], "text")
        process_name = self.tree.set(sel[0], "process")
        if not pid_str.isdigit() or pid_str == "0":
            messagebox.showinfo(
                "PID неизвестен",
                f"Для порта {port} не удалось определить PID процесса (нет прав на просмотр).\n"
                "Перезапустите приложение от администратора кнопкой выше — тогда PID станет виден "
                "и порт можно будет освободить.",
            )
            return
        pid = int(pid_str)

        confirmed = messagebox.askyesno(
            "Завершить процесс",
            f"Завершить процесс {process_name} (PID {pid}), занимающий порт {port}?",
        )
        if not confirmed:
            return

        # шаг 1: обычное завершение без прав администратора
        ok, message = kill_pid_plain(pid)

        # шаг 2: если отказано в доступе - просим elevation именно на эту операцию
        if not ok and self._looks_like_access_denied(message):
            self.status_bar.config(text="Недостаточно прав, запрашиваю права администратора...")
            ok, message = kill_pid_elevated(pid)

        if ok:
            self.status_bar.config(text=message)
        else:
            messagebox.showerror("Не удалось завершить процесс", message)

        self._refresh_now()

    @staticmethod
    def _looks_like_access_denied(message: str) -> bool:
        lowered = message.lower()
        return "access" in lowered or "denied" in lowered or "отказано" in lowered or "5" == lowered.strip()

    def _relaunch_as_admin(self) -> None:
        started = relaunch_as_admin()
        if started:
            self.root.destroy()
        else:
            messagebox.showerror(
                "Не удалось перезапустить",
                "Не получилось запросить права администратора. Попробуйте запустить программу вручную "
                "через 'Запуск от имени администратора'.",
            )


def main() -> None:
    root = tk.Tk()
    PortManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
