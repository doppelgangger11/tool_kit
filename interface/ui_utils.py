import tkinter as tk


def attach(window, root) -> None:
    """
    transient только если главное окно видно: иначе окно, открытое из
    трея или горячей клавишей, спряталось бы вместе со скрытым главным.
    """
    try:
        if root.state() == "normal":
            window.transient(root)
    except tk.TclError:
        pass


def bring_to_front(window) -> None:
    """
    Windows не любит, когда окно появляется поверх других само
    (например, после горячей клавиши). Кратковременный topmost это обходит.
    """
    try:
        window.deiconify()
        window.lift()
        window.focus_force()
        window.attributes("-topmost", True)
        window.after(250, lambda: _release_topmost(window))
    except tk.TclError:
        pass


def _release_topmost(window) -> None:
    try:
        window.attributes("-topmost", False)
    except tk.TclError:
        pass


def center(window) -> None:
    window.update_idletasks()
    width, height = window.winfo_reqwidth(), window.winfo_reqheight()
    x = (window.winfo_screenwidth() - width) // 2
    y = (window.winfo_screenheight() - height) // 3
    window.geometry(f"+{x}+{y}")
