"""
Глобальная горячая клавиша на Windows через RegisterHotKey (без сторонних пакетов).
На других системах start() просто возвращает False.
"""
from __future__ import annotations

import os
import threading

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
WM_HOTKEY, WM_QUIT = 0x0312, 0x0012

_MODS = {
    "alt": MOD_ALT,
    "ctrl": MOD_CONTROL, "control": MOD_CONTROL,
    "shift": MOD_SHIFT,
    "win": MOD_WIN, "super": MOD_WIN,
}

_KEYS = {
    "space": 0x20, "enter": 0x0D, "return": 0x0D, "tab": 0x09,
    "esc": 0x1B, "escape": 0x1B, "backspace": 0x08,
}
_KEYS.update({f"f{i}": 0x6F + i for i in range(1, 13)})


def parse_hotkey(spec: str) -> tuple[int, int]:
    """'ctrl+alt+space' -> (modifiers, virtual_key). ValueError при ошибке."""
    parts = [p.strip().lower() for p in str(spec).split("+") if p.strip()]
    if not parts:
        raise ValueError("empty hotkey")

    *mods, key = parts
    modifiers = 0
    for mod in mods:
        if mod not in _MODS:
            raise ValueError(f"unknown modifier: {mod}")
        modifiers |= _MODS[mod]

    if key in _KEYS:
        vk = _KEYS[key]
    elif len(key) == 1 and key.isalnum() and key.isascii():
        vk = ord(key.upper())
    else:
        raise ValueError(f"unknown key: {key}")

    if not modifiers:
        raise ValueError("hotkey needs at least one modifier")

    return modifiers, vk


class GlobalHotkey:
    def __init__(self):
        self.error: str | None = None
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None

    def start(self, spec: str, callback) -> bool:
        """callback вызывается из ДРУГОГО потока - передавай через dispatcher.call."""
        if os.name != "nt":
            self.error = "global hotkeys are supported on Windows only"
            return False

        try:
            modifiers, vk = parse_hotkey(spec)
        except ValueError as error:
            self.error = f"bad hotkey '{spec}': {error}"
            return False

        ready = threading.Event()
        result = {"ok": False}

        def loop():
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            self._thread_id = kernel32.GetCurrentThreadId()
            result["ok"] = bool(user32.RegisterHotKey(None, 1, modifiers | MOD_NOREPEAT, vk))
            if not result["ok"]:
                self.error = f"'{spec}' is already taken by another program"
            ready.set()

            if not result["ok"]:
                return

            msg = wintypes.MSG()
            try:
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                    if msg.message == WM_HOTKEY:
                        try:
                            callback()
                        except Exception as error:
                            print(f"[Hotkey] callback error: {error!r}")
            finally:
                user32.UnregisterHotKey(None, 1)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
        ready.wait(timeout=2)
        return result["ok"]

    def stop(self):
        if os.name != "nt" or self._thread_id is None:
            return
        import ctypes
        ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
