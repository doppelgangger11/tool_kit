"""
Global hotkey on Windows via RegisterHotKey (without third-party packages).
On other systems, start() simply returns False.
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
    """'ctrl+alt+space' -> (modifiers, virtual_key). ValueError on error."""
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
    """
    Registers one or several global hotkeys and calls the matching callback.

    The callbacks are called from ANOTHER thread - pass them through
    dispatcher.call(...) when they touch Tk.
    """

    def __init__(self):
        self.error: str | None = None
        self.errors: list[str] = []
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None

    def start(self, spec: str, callback) -> bool:
        """One hotkey. True when it was registered."""
        self.start_many([(spec, callback)])

        return not self.errors

    def start_many(self, bindings) -> list[str]:
        """
        bindings: [(spec, callback), ...], e.g. [("ctrl+space", open_launcher)].
        Returns a list of problems (empty when everything was registered).
        A hotkey that fails does not stop the others.
        """
        self.errors = []
        self.error = None

        if os.name != "nt":
            self.errors = ["global hotkeys are supported on Windows only"]
            self.error = self.errors[0]

            return self.errors

        parsed = []

        for spec, callback in bindings:
            try:
                modifiers, vk = parse_hotkey(spec)
            except ValueError as error:
                self.errors.append(f"bad hotkey '{spec}': {error}")
                continue

            parsed.append((spec, modifiers, vk, callback))

        if parsed:
            self._run(parsed)

        self.error = self.errors[0] if self.errors else None

        return self.errors

    def _run(self, parsed) -> None:
        ready = threading.Event()
        callbacks = {}

        def loop():
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            self._thread_id = kernel32.GetCurrentThreadId()

            # RegisterHotKey and the message loop must live in the same thread
            for index, (spec, modifiers, vk, callback) in enumerate(parsed, start=1):
                if user32.RegisterHotKey(None, index, modifiers | MOD_NOREPEAT, vk):
                    callbacks[index] = callback
                else:
                    self.errors.append(f"'{spec}' is already taken by another program")

            ready.set()

            if not callbacks:
                return

            msg = wintypes.MSG()
            try:
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                    if msg.message == WM_HOTKEY:
                        callback = callbacks.get(msg.wParam)

                        if callback is None:
                            continue

                        try:
                            callback()
                        except Exception as error:
                            print(f"[Hotkey] callback error: {error!r}")
            finally:
                for index in callbacks:
                    user32.UnregisterHotKey(None, index)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
        ready.wait(timeout=2)

    def stop(self):
        if os.name != "nt" or self._thread_id is None:
            return
        import ctypes
        ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
