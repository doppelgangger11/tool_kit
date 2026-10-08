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
    Executes functions in the Tk main thread.

    call() can be safely called from any thread:
    from pystray, from a Telegram bot, from a socket, etc.
    """

    def __init__(self, root):
        self.root = root
        self._queue = queue.Queue()
        self._poll()

    def call(self, func, *args, **kwargs):
        self._queue.put((func, args, kwargs))

    def _poll(self):
        # Schedule the next poll IMMEDIATELY: if the function starts a nested
        # loop (wait_window), polling will not stop.
        try:
            self.root.after(POLL_MS, self._poll)
        except tk.TclError:
            return  # The window has already been destroyed.

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
        Ctrl+C / closing from the terminal -> graceful exit.

        Works thanks to periodic polling: without it, Tk on Windows
        does not process signals while there are no events.
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
    Prevents a second daemon instance from being launched.
    A second launch asks the first instance to show the window and exits.
    """

    def __init__(self, port: int = SINGLE_INSTANCE_PORT):
        self.port = port
        self._sock = None
        self._closed = False

    def acquire(self) -> bool:
        """True - we are the first instance, False - another instance is already running."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # On Windows, SO_REUSEADDR would allow a double bind,
        # so it is only enabled on non-Windows systems.
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
        """
        Listens for 'show' requests from subsequent launches.
        on_show is called from another thread.
        """

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
                # shutdown wakes the thread waiting in accept().
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
