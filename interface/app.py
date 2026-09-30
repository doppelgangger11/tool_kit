import customtkinter as ctk

from interface.context import ToolkitContext
from interface.registry import ViewRegistry
from interface.router import Router
from interface.sidebar import Sidebar


class ToolkitApp(ctk.CTk):

    def __init__(self, context: ToolkitContext):
        super().__init__()

        self.context = context
        self.registry = ViewRegistry()

        self.title("Toolkit")
        self.geometry("1100x700")
        self.minsize(900, 600)

        self._build_layout()

    def _build_layout(self):
        self.sidebar = Sidebar(
            self,
            self,
        )

        self.sidebar.pack(
            side="left",
            fill="y",
        )

        self.content = ctk.CTkFrame(
            self,
            corner_radius=0,
        )

        self.content.pack(
            side="right",
            fill="both",
            expand=True,
        )

        self.router = Router(
            self.content,
            self,
        )

    def register(
        self,
        id,
        title,
        view,
        icon="",
        group="TOOLS",
    ):
        self.registry.register(
            id=id,
            title=title,
            view=view,
            icon=icon,
            group=group,
        )

        self.sidebar.rebuild()

    def show(self, view_id):
        self.router.show(view_id)