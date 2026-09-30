import customtkinter as ctk


class View(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(
            parent,
            fg_color="transparent",
        )

        self.app = app
        self.context = app.context

        self.build()

    def build(self):
        pass

    def on_show(self):
        pass

    def on_hide(self):
        pass