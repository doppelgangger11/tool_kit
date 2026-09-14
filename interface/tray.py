import threading
import tkinter as tk

import pystray
from PIL import Image


def setup_tray(root: tk.Tk):
    image = Image.new("RGB", (64, 64), "black")

    def show_window(icon, item):
        root.after(0, root.deiconify)

    def exit_app(icon, item):
        icon.stop()
        root.after(0, root.destroy)

    def hide_window():
        root.withdraw()

    icon = pystray.Icon(
        "Toolkit",
        image,
        "Toolkit",
        menu=pystray.Menu(
            pystray.MenuItem("Open", show_window),
            pystray.MenuItem("Exit", exit_app),
        )
    )

    threading.Thread(
        target=icon.run,
        daemon=True
    ).start()

    root.protocol("WM_DELETE_WINDOW", hide_window)