import threading
import tkinter as tk

import pystray
from PIL import Image, ImageDraw


def _make_icon_image() -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((4, 4, 60, 60), radius=12, fill=(35, 35, 35, 255))
    draw.rectangle((16, 16, 48, 25), fill="white")   # буква T
    draw.rectangle((28, 25, 36, 50), fill="white")
    return image


class Tray:
    """
    Иконка в трее - главный пульт демона.
    Все действия выполняются в главном потоке Tk через dispatcher,
    pystray живёт в своём потоке и Tk напрямую не трогает.
    """

    def __init__(self, root: tk.Tk, dispatcher, actions=(), on_exit=None):
        """
        actions - список (название, функция без аргументов) для меню трея
        on_exit - необязательная функция, вызывается перед закрытием
        """
        self.root = root
        self.dispatch = dispatcher.call
        self.on_exit = on_exit

        self._notified = False
        self._exiting = False

        items = [
            pystray.MenuItem("Open Toolkit", self._cb(self.show_window), default=True),
        ]

        if actions:
            items.append(pystray.Menu.SEPARATOR)
            for label, func in actions:
                items.append(pystray.MenuItem(label, self._cb(func)))

        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Exit", self._cb(self.exit_app)))

        self.icon = pystray.Icon(
            "Toolkit",
            _make_icon_image(),
            "Toolkit",
            menu=pystray.Menu(*items),
        )

        # крестик окна не завершает демон, а прячет окно
        root.protocol("WM_DELETE_WINDOW", self.hide_window)

    def _cb(self, func):
        def handler(icon, item):
            self.dispatch(func)
        return handler

    # ---- выполняются в главном потоке ----

    def show_window(self):
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

    def hide_window(self):
        self.root.withdraw()

        if not self._notified:
            self._notified = True
            try:
                self.icon.notify("Toolkit keeps running in the tray.", "Toolkit")
            except Exception:
                pass

    def exit_app(self):
        if self._exiting:
            return
        self._exiting = True

        self.stop()

        if self.on_exit:
            try:
                self.on_exit()
            except Exception as error:
                print(f"[Tray] on_exit error: {error!r}")

        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # ---- управление иконкой ----

    def start(self):
        threading.Thread(target=self.icon.run, daemon=True).start()

    def stop(self):
        try:
            self.icon.stop()
        except Exception:
            pass
