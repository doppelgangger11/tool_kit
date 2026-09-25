"""
Работа с правами администратора под Windows (UAC).

Два сценария использования:
1. is_admin() - проверить, запущен ли сам процесс от админа.
2. relaunch_as_admin() - перезапустить всё приложение с правами админа
   (показывает стандартный UAC-диалог Windows).
3. kill_pid_elevated(pid) - точечно поднять права ТОЛЬКО для команды
   завершения процесса, без перезапуска всего приложения. Это лучше
   с точки зрения UX: обычный kill пробуем без прав админа, и только
   если он не сработал (Access Denied) - всплывает UAC-запрос именно
   на эту операцию, через отдельный процесс taskkill.

Механизм - ShellExecuteW с verb="runas". Это стандартный Windows API
для запроса elevation, обёрнутый через ctypes (без сторонних зависимостей
вроде pywin32).
"""

from __future__ import annotations

import ctypes
import subprocess
import sys


IS_WINDOWS = sys.platform.startswith("win")


def is_admin() -> bool:
    """True, если текущий процесс уже запущен с правами администратора."""
    if not IS_WINDOWS:
        import os
        return os.geteuid() == 0  # type: ignore[attr-defined]
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    """
    Перезапустить весь текущий скрипт с правами администратора через UAC.
    Вызывающий код должен после успешного вызова сам закрыть текущий
    (неэлевированный) процесс - relaunch не завершает его автоматически.

    Возвращает True, если запрос на elevation был отправлен (пользователь
    увидит UAC-диалог); False, если платформа не Windows или что-то
    пошло не так на уровне ОС.
    """
    if not IS_WINDOWS:
        return False

    params = " ".join(f'"{arg}"' for arg in sys.argv)
    try:
        result = ctypes.windll.shell32.ShellExecuteW(  # type: ignore[attr-defined]
            None, "runas", sys.executable, params, None, 1
        )
        # ShellExecuteW возвращает значение > 32 при успехе
        return int(result) > 32
    except Exception:
        return False


def kill_pid_elevated(pid: int) -> tuple[bool, str]:
    """
    Завершить процесс с запросом прав администратора именно на эту операцию
    (показывается системный UAC-диалог), не перезапуская весь GUI.

    Реализовано через ShellExecuteW("runas", "taskkill", "/F /T /PID <pid>"):
    Windows сам поднимет новый elevated-процесс taskkill.exe и покажет
    диалог согласия пользователю.

    Возвращает (успех, сообщение_для_пользователя).
    """
    if not IS_WINDOWS:
        return False, "Elevated kill поддерживается только на Windows"

    try:
        result = ctypes.windll.shell32.ShellExecuteW(  # type: ignore[attr-defined]
            None, "runas", "taskkill", f"/F /T /PID {pid}", None, 0
        )
        code = int(result)
        if code > 32:
            return True, "Запрос на завершение отправлен (подтвердите в диалоге UAC, если он появится)"
        if code == 5:
            return False, "Пользователь отклонил запрос на права администратора (UAC)"
        return False, f"Не удалось запустить elevated taskkill (код {code})"
    except Exception as e:
        return False, f"Ошибка при запросе прав администратора: {e}"


def kill_pid_plain(pid: int) -> tuple[bool, str]:
    """Обычное завершение без запроса прав - пробуем в первую очередь."""
    if IS_WINDOWS:
        proc = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True, text=True,
        )
        if proc.returncode == 0:
            return True, "Процесс завершён"
        return False, proc.stderr.strip() or proc.stdout.strip() or "Неизвестная ошибка"
    else:
        try:
            import psutil
            psutil.Process(pid).kill()
            return True, "Процесс завершён"
        except Exception as e:
            return False, str(e)
