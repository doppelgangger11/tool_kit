from __future__ import annotations

import ctypes
import os
import re
import threading
import traceback

from typing import Callable, NamedTuple


# ---------------------------------------------------------
# Parsing "Ctrl+Alt+N"
# ---------------------------------------------------------

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

MODIFIERS = {
    "ctrl": MOD_CONTROL, "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN, "windows": MOD_WIN, "super": MOD_WIN,
}

# порядок и написание в итоговой записи
_MOD_ORDER = (
    (MOD_CONTROL, "Ctrl"), (MOD_ALT, "Alt"),
    (MOD_SHIFT, "Shift"), (MOD_WIN, "Win"),
)

NAMED_KEYS = {
    "space": 0x20, "enter": 0x0D, "return": 0x0D, "tab": 0x09,
    "esc": 0x1B, "escape": 0x1B,
    "insert": 0x2D, "ins": 0x2D, "delete": 0x2E, "del": 0x2E,
    "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pgup": 0x21, "pagedown": 0x22, "pgdn": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
}

_NAMED_DISPLAY = {
    0x20: "Space", 0x0D: "Enter", 0x09: "Tab", 0x1B: "Esc", 0x2D: "Insert",
    0x2E: "Delete", 0x24: "Home", 0x23: "End", 0x21: "PageUp",
    0x22: "PageDown", 0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down",
}


def parse_hotkey(text: str):
    """
    'ctrl + alt + n' -> (modificators, key codes, 'Ctrl+Alt+N').
    At least one modifier is required: otherwise, the hotkey would intercept the.
    """
    parts = [p for p in text.replace(" ", "").split("+") if p]

    if len(parts) < 2:
        raise ValueError("Use a modifier and a key, for example Ctrl+Alt+N.")

    *mod_names, key = parts
    mods = 0

    for name in mod_names:
        flag = MODIFIERS.get(name.lower())
        if flag is None:
            raise ValueError(f"Unknown modifier: {name}")
        if mods & flag:
            raise ValueError(f"Modifier repeated: {name}")
        mods |= flag

    lowered = key.lower()

    if len(key) == 1 and key.isalnum() and key.isascii():
        vk = ord(key.upper())
        display = key.upper()
    elif re.fullmatch(r"f(\d{1,2})", lowered) and 1 <= int(lowered[1:]) <= 24:
        vk = 0x70 + int(lowered[1:]) - 1
        display = f"F{int(lowered[1:])}"
    elif lowered in NAMED_KEYS:
        vk = NAMED_KEYS[lowered]
        display = _NAMED_DISPLAY[vk]
    else:
        raise ValueError(f"Unknown key: {key}")

    canonical = "+".join(
        [label for flag, label in _MOD_ORDER if mods & flag] + [display]
    )

    return mods, vk, canonical


# ---------------------------------------------------------
# Windows API layer (подменяется в тестах)
# ---------------------------------------------------------

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
WM_USER = 0x0400
ERROR_HOTKEY_ALREADY_REGISTERED = 1409


class WinApi:
    def __init__(self):
        from ctypes import wintypes

        self._wintypes = wintypes
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        self.user32.RegisterHotKey.argtypes = [
            wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT,
        ]
        self.user32.RegisterHotKey.restype = wintypes.BOOL

        self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.UnregisterHotKey.restype = wintypes.BOOL

        self.user32.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG), wintypes.HWND,
            wintypes.UINT, wintypes.UINT,
        ]
        self.user32.GetMessageW.restype = ctypes.c_int

        self.user32.PeekMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG), wintypes.HWND,
            wintypes.UINT, wintypes.UINT, wintypes.UINT,
        ]
        self.user32.PeekMessageW.restype = wintypes.BOOL

        self.user32.PostThreadMessageW.argtypes = [
            wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
        ]
        self.user32.PostThreadMessageW.restype = wintypes.BOOL

        self.kernel32.GetCurrentThreadId.restype = wintypes.DWORD

    def prepare_queue(self):
        msg = self._wintypes.MSG()
        self.user32.PeekMessageW(ctypes.byref(msg), None, WM_USER, WM_USER, 0)

    def thread_id(self) -> int:
        return int(self.kernel32.GetCurrentThreadId())

    def register(self, hotkey_id: int, mods: int, vk: int) -> int:
        if self.user32.RegisterHotKey(None, hotkey_id, mods, vk):
            return 0
        return ctypes.get_last_error() or -1

    def unregister(self, hotkey_id: int) -> None:
        self.user32.UnregisterHotKey(None, hotkey_id)

    def get_message(self):
        msg = self._wintypes.MSG()
        result = self.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)

        if result == 0:
            return "quit", 0
        if result == -1:
            return "error", 0
        if msg.message == WM_HOTKEY:
            return "hotkey", int(msg.wParam)

        return "other", 0

    def post_quit(self, thread_id: int) -> None:
        self.user32.PostThreadMessageW(thread_id, WM_QUIT, 0, 0)


def describe_error(code: int) -> str:
    if code == ERROR_HOTKEY_ALREADY_REGISTERED:
        return "already used by another program"
    return f"Windows error {code}"


# ---------------------------------------------------------
# Manager
# ---------------------------------------------------------

class Binding(NamedTuple):
    name: str
    mods: int
    vk: int
    callback: Callable


class HotkeyManager:
    def __init__(self, dispatch: Callable, api=None):
        self._dispatch = dispatch

        if api is not None:
            self._api = api
        else:
            self._api = WinApi() if os.name == "nt" else None

        self._bindings: dict[int, Binding] = {}
        self._next_id = 1
        self._thread: threading.Thread | None = None
        self._thread_id = 0

        self.errors: dict[str, str] = {}   # name -> err text ('' = ok)

    def add(self, name: str, combo: str, callback: Callable) -> str:
        mods, vk, canonical = parse_hotkey(combo)
        self._bindings[self._next_id] = Binding(name, mods, vk, callback)
        self._next_id += 1
        return canonical

    def start(self) -> dict[str, str]:
        if self._api is None:
            self.errors = {
                b.name: "global hotkeys work only on Windows"
                for b in self._bindings.values()
            }
            return dict(self.errors)

        if not self._bindings:
            return {}

        ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run, args=(ready,), daemon=True, name="hotkeys"
        )
        self._thread.start()
        ready.wait(5)

        return dict(self.errors)

    def stop(self) -> None:
        thread = self._thread
        if thread is None:
            return

        if thread.is_alive() and self._thread_id:
            self._api.post_quit(self._thread_id)
            thread.join(3)

        self._thread = None
        self._thread_id = 0

    # ---- flow ----

    def _run(self, ready: threading.Event) -> None:
        api = self._api
        registered = []

        try:
            api.prepare_queue()
            self._thread_id = api.thread_id()

            for hotkey_id, binding in self._bindings.items():
                code = api.register(
                    hotkey_id, binding.mods | MOD_NOREPEAT, binding.vk
                )
                self.errors[binding.name] = "" if code == 0 else describe_error(code)
                if code == 0:
                    registered.append(hotkey_id)
        finally:
            ready.set()

        try:
            while True:
                kind, value = api.get_message()

                if kind in ("quit", "error"):
                    break

                if kind == "hotkey":
                    binding = self._bindings.get(value)
                    if binding:
                        self._dispatch(lambda b=binding: self._safe(b))
        finally:
            for hotkey_id in registered:
                api.unregister(hotkey_id)

    @staticmethod
    def _safe(binding: Binding) -> None:
        try:
            binding.callback()
        except Exception:
            print(f"[Hotkeys] action '{binding.name}' failed:")
            traceback.print_exc()


# ---------------------------------------------------------
# Service: manager + settings
# ---------------------------------------------------------

class HotkeyService:
    """
    actions  - {key: (name, func)}
    settings - settings dictionary, keyboard shortcuts takes from [HOTKEYS]
    status   - {key: (status, message)}: ok | disabled | error
    """

    def __init__(self, dispatch: Callable, actions: dict, settings: dict, api=None):
        self._dispatch = dispatch
        self.actions = actions
        self.settings = settings
        self._api = api
        self._manager: HotkeyManager | None = None
        self.status: dict[str, tuple[str, str]] = {}

    def combo_for(self, key: str) -> str:
        return str(self.settings.get("HOTKEYS", {}).get(key, "") or "").strip()

    def apply(self) -> dict[str, tuple[str, str]]:
        self.stop()

        manager = HotkeyManager(self._dispatch, self._api)
        status: dict[str, tuple[str, str]] = {}
        used: dict[str, str] = {}

        for key, (title, func) in self.actions.items():
            combo = self.combo_for(key)

            if not combo:
                status[key] = ("disabled", "")
                continue

            try:
                _, _, canonical = parse_hotkey(combo)
            except ValueError as error:
                status[key] = ("error", str(error))
                continue

            if canonical in used:
                status[key] = ("error", f"same as '{used[canonical]}'")
                continue

            used[canonical] = title
            manager.add(key, combo, func)
            status[key] = ("ok", canonical)

        results = manager.start()

        for key, error in results.items():
            if error:
                status[key] = ("error", error)

        self._manager = manager
        self.status = status
        return status

    def stop(self) -> None:
        if self._manager is not None:
            self._manager.stop()
            self._manager = None
