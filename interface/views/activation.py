import customtkinter as ctk

from interface.view import View
from scripts.activation_new_task import activate_new_task


class ActivationView(View):

    def build(self):
        ctk.CTkLabel(
            self,
            text="Activate new task",
            font=("Arial", 26, "bold"),
        ).pack(
            padx=30,
            pady=(30, 20),
            anchor="w",
        )

        self.task_name = ctk.CTkEntry(
            self,
            placeholder_text="Task name",
            width=400,
        )
        self.task_name.pack(
            padx=30,
            pady=10,
            anchor="w",
        )

        self.activate_button = ctk.CTkButton(
            self,
            text="Activate",
            command=self.activate,
        )
        self.activate_button.pack(
            padx=30,
            pady=20,
            anchor="w",
        )

    def activate(self):
        name = self.task_name.get().strip()

        if not name:
            return

        settings = self.context.settings

        base_dir = (
            self.context.base_dir
            / settings["DIRS"]["working_dir"]
        )

        tmp_dir = (
            self.context.base_dir
            / settings["DIRS"]["temp_dir"]
        )

        activate_new_task(
            base_dir=base_dir,
            name_of_task=name,
            tmp_dir=tmp_dir,
        )