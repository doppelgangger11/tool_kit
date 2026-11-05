"""
Небольшие анимации для Tkinter без перезаписи интерфейса.

Всё работает через widget.after(): окно не блокируется. Прогресс считается
по времени (а не по числу кадров), поэтому длительность одинакова
на быстром и медленном компьютере.

    anim.configure(settings["BASE"].get("animations", True))
    anim.fade_in(window)
    anim.hover(button, "#f0f0f0", "#dbe7f6")
    anim.flash(label, "#ffd6d6")
"""

from __future__ import annotations

import os
import time
import tkinter as tk

from typing import Callable


ENABLED = True
FRAME_MS = 16               # ~60 кадров в секунду

EASINGS: dict[str, Callable[[float], float]] = {
    "linear": lambda t: t,
    "ease_out": lambda t: 1 - (1 - t) ** 3,
    "ease_in": lambda t: t ** 3,
    "ease_in_out": lambda t: 3 * t * t - 2 * t ** 3,
}


# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------

def system_animations_enabled() -> bool:
    """Уважаем настройку Windows «Показывать анимацию в Windows»."""
    if os.name != "nt":
        return True

    try:
        import ctypes

        flag = ctypes.c_int(1)
        ok = ctypes.windll.user32.SystemParametersInfoW(   # SPI_GETCLIENTAREAANIMATION
            0x1042, 0, ctypes.byref(flag), 0
        )
        return bool(flag.value) if ok else True
    except Exception:
        return True


def configure(enabled=True, respect_system: bool = True) -> bool:
    """Включает или выключает все анимации. Возвращает итоговое состояние."""
    global ENABLED

    wanted = str(enabled).strip().lower() not in ("false", "off", "no", "0", "none")
    ENABLED = wanted and (system_animations_enabled() if respect_system else True)
    return ENABLED


# ---------------------------------------------------------
# Core: tween
# ---------------------------------------------------------

_jobs: dict[tuple[str, str], str] = {}


def cancel(widget, key: str = "default") -> None:
    """Останавливает анимацию с этим ключом на этом виджете."""
    job = _jobs.pop((str(widget), key), None)

    if job is not None:
        try:
            widget.after_cancel(job)
        except tk.TclError:
            pass


def tween(
    widget,
    duration_ms: float,
    update: Callable[[float], None],
    *,
    easing="ease_out",
    key: str = "default",
    on_done: Callable[[], None] | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """
    Вызывает update(p) с p от 0 до 1 (со сглаживанием) в течение duration_ms.
    Новая анимация с тем же ключом на том же виджете отменяет предыдущую.
    Если анимации выключены, сразу применяется конечное состояние.
    """
    ease = EASINGS[easing] if isinstance(easing, str) else easing
    slot = (str(widget), key)

    cancel(widget, key)

    if not ENABLED or duration_ms <= 0:
        update(1.0)
        if on_done:
            on_done()
        return

    started = clock()

    def step():
        try:
            if not widget.winfo_exists():
                _jobs.pop(slot, None)
                return

            progress = min((clock() - started) * 1000.0 / duration_ms, 1.0)
            update(ease(progress))

            if progress >= 1.0:
                _jobs.pop(slot, None)
                if on_done:
                    on_done()
            else:
                _jobs[slot] = widget.after(FRAME_MS, step)

        except tk.TclError:
            _jobs.pop(slot, None)          # окно закрыли посреди анимации

    update(0.0)
    _jobs[slot] = widget.after(FRAME_MS, step)


# ---------------------------------------------------------
# Windows: fades
# ---------------------------------------------------------

def _set_alpha(window, value: float) -> bool:
    try:
        window.attributes("-alpha", max(0.0, min(1.0, value)))
        return True
    except tk.TclError:
        return False        # прозрачность не поддерживается: тихо пропускаем


def fade_in(window, ms: float = 180, then: Callable | None = None) -> None:
    """Плавно показывает окно (в том числе спрятанное через withdraw)."""
    if not ENABLED or not _set_alpha(window, 0.0):
        try:
            window.deiconify()
        except tk.TclError:
            pass
        if then:
            then()
        return

    try:
        if window.state() == "withdrawn":
            window.deiconify()
    except tk.TclError:
        pass

    tween(
        window, ms, lambda p: _set_alpha(window, p),
        key="fade", on_done=lambda: (_set_alpha(window, 1.0), then and then()),
    )


def fade_out(window, ms: float = 140, then: Callable | None = None) -> None:
    """Плавно скрывает окно, затем вызывает then (withdraw, destroy и т.п.)."""
    if not ENABLED or not _set_alpha(window, 1.0):
        if then:
            then()
        return

    tween(
        window, ms, lambda p: _set_alpha(window, 1.0 - p),
        easing="ease_in", key="fade", on_done=lambda: then and then(),
    )


# ---------------------------------------------------------
# Widgets: color
# ---------------------------------------------------------

def _rgb(widget, color: str) -> tuple[int, int, int]:
    r, g, b = widget.winfo_rgb(color)          # 16 бит на канал, понимает имена цветов
    return r >> 8, g >> 8, b >> 8


def _mix(a, b, p: float) -> str:
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * p) for x, y in zip(a, b))


def animate_color(
    widget,
    option: str,
    to_color: str,
    ms: float = 150,
    *,
    from_color: str | None = None,
    easing="ease_out",
    on_done: Callable | None = None,
) -> None:
    """Плавно меняет цветовую опцию виджета (bg, fg, ...)."""
    try:
        start = _rgb(widget, from_color or widget.cget(option))
        end = _rgb(widget, to_color)
    except tk.TclError:
        return

    tween(
        widget, ms,
        lambda p: widget.configure(**{option: _mix(start, end, p)}),
        easing=easing, key=f"color-{option}", on_done=on_done,
    )


def hover(widget, normal: str, over: str, ms: float = 120, option: str = "bg") -> None:
    """Плавная подсветка при наведении. Существующие привязки не трогает."""
    widget.bind("<Enter>", lambda e: animate_color(widget, option, over, ms), add="+")
    widget.bind("<Leave>", lambda e: animate_color(widget, option, normal, ms), add="+")


def flash(widget, color: str = "#ffd6d6", ms: float = 400, option: str = "bg") -> None:
    """Короткая вспышка цветом с возвратом (ошибка, подтверждение)."""
    try:
        original = widget.cget(option)
    except tk.TclError:
        return

    animate_color(widget, option, original, ms, from_color=color)


# ---------------------------------------------------------
# Sequences
# ---------------------------------------------------------

def stagger(widget, calls: list[Callable], step_ms: float = 12) -> None:
    """Вызывает функции по очереди с задержкой: эффект «волны»."""
    if not ENABLED:
        for call in calls:
            call()
        return

    for index, call in enumerate(calls):
        widget.after(int(index * step_ms), call)


def spinner(label, text: str = "Working", interval_ms: int = 100) -> Callable[[], None]:
    """
    Крутящийся индикатор в тексте Label на время долгой операции.
    Возвращает функцию остановки.
    """
    frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    state = {"i": 0, "job": None, "running": True}

    def tick():
        if not state["running"]:
            return
        try:
            label.config(text=f"{frames[state['i'] % len(frames)]} {text}")
            state["i"] += 1
            state["job"] = label.after(interval_ms, tick)
        except tk.TclError:
            state["running"] = False

    def stop():
        state["running"] = False
        if state["job"] is not None:
            try:
                label.after_cancel(state["job"])
            except tk.TclError:
                pass

    tick()
    return stop