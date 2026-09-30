import customtkinter as ctk


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(
            parent,
            width=220,
            corner_radius=0,
        )

        self.app = app

        self.logo = ctk.CTkLabel(
            self,
            text="◈ TOOLKIT",
            font=("Arial", 22, "bold"),
        )
        self.logo.pack(
            padx=20,
            pady=(25, 30),
        )

        self.buttons_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        self.buttons_frame.pack(
            fill="both",
            expand=True,
        )

    def rebuild(self):
        for widget in self.buttons_frame.winfo_children():
            widget.destroy()

        groups = self.app.registry.groups()

        for group, views in groups.items():
            ctk.CTkLabel(
                self.buttons_frame,
                text=group,
                anchor="w",
                font=("Arial", 11, "bold"),
            ).pack(
                fill="x",
                padx=20,
                pady=(10, 5),
            )

            for definition in views:
                ctk.CTkButton(
                    self.buttons_frame,
                    text=f"{definition.icon}  {definition.title}",
                    anchor="w",
                    fg_color="transparent",
                    command=lambda id=definition.id:
                        self.app.show(id),
                ).pack(
                    fill="x",
                    padx=10,
                    pady=2,
                )