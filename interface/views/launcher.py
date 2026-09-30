from interface.view import View
from scripts.program_launcher import launch_selected_programs

import customtkinter as ctk


class LauncherView(View):

    def build(self):
        ctk.CTkLabel(
            self,
            text="Launch work setup",
            font=("Arial", 26, "bold"),
        ).pack(
            padx=30,
            pady=(30, 10),
            anchor="w",
        )

        ctk.CTkLabel(
            self,
            text="Launch configured programs.",
        ).pack(
            padx=30,
            pady=(0, 20),
            anchor="w",
        )

        ctk.CTkButton(
            self,
            text="🚀 Launch",
            command=self.launch,
        ).pack(
            padx=30,
            pady=10,
            anchor="w",
        )

    def launch(self):
        launch_selected_programs(
            self.context.settings
        )