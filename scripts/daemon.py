import os
import queue
import signal
import socket
import threading
import traceback
import tkinter as tk


SINGLE_INSTANCE_HOST = "127.0.0.1"
SINGLE_INSTANCE_PORT = 47653
POLL_MS = 100


class Dispatcher:
    """
    Выполняет функции в главном потоке Tk.
    call() можно безопасно вызывать из любого потока:
    из pystray, из Telegram-бота, из сокета и т.д.
    """

    def __init__(self, root):
        self.root = root
        self._queue = queue.Queue()
        self._poll()

    def call(self, func, *args, **kwargs):
        self._queue.put((func, args, kwargs))

    def _poll(self):
        # следующий опрос планируем СРАЗУ: если функция запустит вложенный
        # цикл (wait_window), опрос не остановится
        try:
            self.root.after(POLL_MS, self._poll)
        except tk.TclError:
            return  # окно уже уничтожено

        while True:
            try:
                func, args, kwargs = self._queue.get_nowait()
            except queue.Empty:
                break

            try:
                func(*args, **kwargs)
            except Exception:
                traceback.print_exc()

    def install_signal_handlers(self, on_quit):
        """
        Ctrl+C / закрытие из терминала -> корректный выход.
        Работает благодаря периодическому опросу: без него Tk на Windows
        не пропускает сигналы, пока нет событий.
        """

        def handler(signum, frame):
            self.call(on_quit)

        for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
            sig = getattr(signal, name, None)
            if sig is None:
                continue
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass


class SingleInstance:
    """
    Не даёт запустить второй демон. Второй запуск просит первый
    показать окно и завершается.
    """

    def __init__(self, port: int = SINGLE_INSTANCE_PORT):
        self.port = port
        self._sock = None
        self._closed = False

    def acquire(self) -> bool:
        """True - мы первый экземпляр, False - уже запущен другой."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # на Windows SO_REUSEADDR разрешил бы двойной bind, поэтому только не-Windows
        if os.name != "nt":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            sock.bind((SINGLE_INSTANCE_HOST, self.port))
            sock.listen(5)
        except OSError:
            sock.close()
            self._ask_existing_to_show()
            return False

        self._sock = sock
        return True

    def _ask_existing_to_show(self) -> bool:
        try:
            with socket.create_connection(
                (SINGLE_INSTANCE_HOST, self.port), timeout=1
            ) as conn:
                conn.sendall(b"show")
                conn.settimeout(1)
                return conn.recv(8) == b"ok"
        except OSError:
            return False

    def serve(self, on_show):
        """Слушает запросы 'show' от повторных запусков. on_show зовётся из другого потока."""

        def loop():
            while not self._closed:
                try:
                    conn, _ = self._sock.accept()
                except OSError:
                    break

                with conn:
                    try:
                        conn.settimeout(1)
                        if conn.recv(16) == b"show":
                            on_show()
                            conn.sendall(b"ok")
                    except OSError:
                        pass

        threading.Thread(target=loop, daemon=True).start()

    def close(self):
        self._closed = True
        if self._sock is not None:
            try:
                # shutdown будит поток, ждущий в accept()
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
