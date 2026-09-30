import os
import subprocess
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from interface.view import View
from scripts.quick_commands_manager import Command


class QuickCommandsView(View):
    def build(self):
        self.selected_group = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_content()

        self.refresh()

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _build_header(self):
        header = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )

        header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=30,
            pady=(30, 15),
        )

        header.grid_columnconfigure(0, weight=1)

        title_frame = ctk.CTkFrame(
            header,
            fg_color="transparent",
        )
        title_frame.grid(
            row=0,
            column=0,
            sticky="w",
        )

        ctk.CTkLabel(
            title_frame,
            text="Quick Commands",
            font=ctk.CTkFont(
                size=28,
                weight="bold",
            ),
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_frame,
            text="Frequently used commands and tools.",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray70"),
        ).pack(
            anchor="w",
            pady=(4, 0),
        )

        ctk.CTkButton(
            header,
            text="+ Command",
            width=120,
            command=self.open_add_command,
        ).grid(
            row=0,
            column=1,
            padx=(10, 0),
        )

        ctk.CTkButton(
            header,
            text="+ Group",
            width=100,
            fg_color="transparent",
            border_width=1,
            command=self.open_add_group,
        ).grid(
            row=0,
            column=2,
            padx=(10, 0),
        )

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------

    def _build_content(self):
        content = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )

        content.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=24,
            pady=(0, 20),
        )

        content.grid_columnconfigure(
            0,
            weight=0,
            minsize=190,
        )

        content.grid_columnconfigure(
            1,
            weight=1,
        )

        content.grid_rowconfigure(
            0,
            weight=1,
        )

        # --------------------------------------------------------------
        # Groups
        # --------------------------------------------------------------

        self.groups_frame = ctk.CTkFrame(
            content,
            corner_radius=12,
        )

        self.groups_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(6, 10),
        )

        ctk.CTkLabel(
            self.groups_frame,
            text="Groups",
            font=ctk.CTkFont(
                size=15,
                weight="bold",
            ),
        ).pack(
            anchor="w",
            padx=15,
            pady=(15, 10),
        )

        self.groups_list = ctk.CTkScrollableFrame(
            self.groups_frame,
            fg_color="transparent",
        )

        self.groups_list.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=(0, 5),
        )

        # --------------------------------------------------------------
        # Commands
        # --------------------------------------------------------------

        self.commands_frame = ctk.CTkFrame(
            content,
            corner_radius=12,
        )

        self.commands_frame.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(0, 6),
        )

        self.commands_frame.grid_rowconfigure(
            1,
            weight=1,
        )

        self.commands_title = ctk.CTkLabel(
            self.commands_frame,
            text="Commands",
            font=ctk.CTkFont(
                size=20,
                weight="bold",
            ),
        )

        self.commands_title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(18, 10),
        )

        self.commands_list = ctk.CTkScrollableFrame(
            self.commands_frame,
            fg_color="transparent",
        )

        self.commands_list.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=10,
            pady=(0, 10),
        )

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self):
        groups = self.context.quick_commands_manager.get_groups()

        commands = self.context.quick_commands_manager.get_commands()

        if self.selected_group not in groups:
            self.selected_group = groups[0] if groups else None

        self._refresh_groups(groups)
        self._refresh_commands(commands)

    def _refresh_groups(self, groups):
        for widget in self.groups_list.winfo_children():
            widget.destroy()

        if not groups:
            ctk.CTkLabel(
                self.groups_list,
                text="No groups",
                text_color=("gray50", "gray60"),
            ).pack(
                pady=20,
            )
            return

        for group in groups:
            self._create_group_button(group)

    def _refresh_commands(self, commands):
        for widget in self.commands_list.winfo_children():
            widget.destroy()

        if self.selected_group is None:
            self.commands_title.configure(
                text="Commands"
            )

            ctk.CTkLabel(
                self.commands_list,
                text="Create a group to add commands.",
                text_color=("gray50", "gray60"),
            ).pack(
                pady=30,
            )

            return

        self.commands_title.configure(
            text=self.selected_group
        )

        group_commands = [
            command
            for command in commands
            if command.group == self.selected_group
        ]

        if not group_commands:
            ctk.CTkLabel(
                self.commands_list,
                text="No commands in this group.",
                text_color=("gray50", "gray60"),
            ).pack(
                pady=30,
            )
            return

        for command in group_commands:
            self._create_command_card(command)

    # ------------------------------------------------------------------
    # Group UI
    # ------------------------------------------------------------------

    def _create_group_button(self, group):
        selected = group == self.selected_group

        frame = ctk.CTkFrame(
            self.groups_list,
            fg_color=(
                ("gray75", "gray25")
                if selected
                else "transparent"
            ),
            corner_radius=8,
        )

        frame.pack(
            fill="x",
            padx=3,
            pady=2,
        )

        frame.grid_columnconfigure(
            0,
            weight=1,
        )

        button = ctk.CTkButton(
            frame,
            text=group,
            anchor="w",
            fg_color="transparent",
            hover_color=("gray70", "gray30"),
            command=lambda: self.select_group(group),
        )

        button.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        menu_button = ctk.CTkButton(
            frame,
            text="⋮",
            width=30,
            fg_color="transparent",
            hover_color=("gray70", "gray30"),
            command=lambda: self.open_group_menu(group),
        )

        menu_button.grid(
            row=0,
            column=1,
            padx=2,
        )

    def select_group(self, group):
        self.selected_group = group
        self.refresh()

    # ------------------------------------------------------------------
    # Group actions
    # ------------------------------------------------------------------

    def open_add_group(self):
        dialog = GroupDialog(
            self,
            title="Add Group",
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            self.context.quick_commands_manager.add_group(
                dialog.result
            )

        except ValueError as error:
            messagebox.showerror(
                "Error",
                str(error),
                parent=self,
            )
            return

        self.selected_group = dialog.result
        self.refresh()

    def open_group_menu(self, group):
        dialog = GroupMenuDialog(
            self,
            group,
        )

        self.wait_window(dialog)

        if dialog.result == "delete":
            self.delete_group(group)

    def delete_group(self, group):
        commands = self.context.quick_commands_manager.get_commands()

        group_commands = [
            command
            for command in commands
            if command.group == group
        ]

        if group_commands:
            confirmed = messagebox.askyesno(
                "Delete group",
                (
                    f"Group '{group}' contains "
                    f"{len(group_commands)} command(s).\n\n"
                    "Delete the group and all its commands?"
                ),
                parent=self,
            )

            if not confirmed:
                return

        else:
            confirmed = messagebox.askyesno(
                "Delete group",
                f"Delete group '{group}'?",
                parent=self,
            )

            if not confirmed:
                return

        try:
            self.context.quick_commands_manager.remove_group(
                group
            )

        except ValueError as error:
            messagebox.showerror(
                "Error",
                str(error),
                parent=self,
            )
            return

        self.selected_group = None
        self.refresh()

    # ------------------------------------------------------------------
    # Command cards
    # ------------------------------------------------------------------

    def _create_command_card(self, command: Command):
        card = ctk.CTkFrame(
            self.commands_list,
            corner_radius=10,
        )

        card.pack(
            fill="x",
            padx=5,
            pady=5,
        )

        card.grid_columnconfigure(
            0,
            weight=1,
        )

        # --------------------------------------------------------------
        # Information
        # --------------------------------------------------------------

        info = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )

        info.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=15,
            pady=12,
        )

        ctk.CTkLabel(
            info,
            text=command.name,
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
            anchor="w",
        ).pack(
            anchor="w",
        )

        command_text = command.command

        if command.parameter:
            command_text += f" {command.parameter}"

        ctk.CTkLabel(
            info,
            text=command_text,
            font=ctk.CTkFont(
                size=11,
            ),
            text_color=("gray40", "gray70"),
            anchor="w",
        ).pack(
            anchor="w",
            pady=(3, 0),
        )

        if command.admin:
            ctk.CTkLabel(
                info,
                text="Administrator",
                font=ctk.CTkFont(size=10),
                text_color=("gray45", "gray65"),
            ).pack(
                anchor="w",
                pady=(3, 0),
            )

        # --------------------------------------------------------------
        # Buttons
        # --------------------------------------------------------------

        actions = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )

        actions.grid(
            row=0,
            column=1,
            padx=10,
        )

        ctk.CTkButton(
            actions,
            text="Run",
            width=70,
            command=lambda c=command: self.run_command(c),
        ).pack(
            side="left",
            padx=3,
        )

        ctk.CTkButton(
            actions,
            text="Edit",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=lambda c=command: self.open_edit_command(c),
        ).pack(
            side="left",
            padx=3,
        )

        ctk.CTkButton(
            actions,
            text="Delete",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=lambda c=command: self.delete_command(c),
        ).pack(
            side="left",
            padx=3,
        )

    # ------------------------------------------------------------------
    # Command actions
    # ------------------------------------------------------------------

    def open_add_command(self):
        groups = self.context.quick_commands_manager.get_groups()

        if not groups:
            messagebox.showwarning(
                "No groups",
                "Create a group first.",
                parent=self,
            )
            return

        dialog = CommandDialog(
            self,
            title="Add Command",
            groups=groups,
            selected_group=self.selected_group,
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            self.context.quick_commands_manager.add_command(
                group=dialog.result["group"],
                name=dialog.result["name"],
                command=dialog.result["command"],
                parameter=dialog.result["parameter"],
                admin=dialog.result["admin"],
            )

        except ValueError as error:
            messagebox.showerror(
                "Error",
                str(error),
                parent=self,
            )
            return

        self.selected_group = dialog.result["group"]

        self.refresh()

    def open_edit_command(self, command):
        groups = self.context.quick_commands_manager.get_groups()

        dialog = CommandDialog(
            self,
            title="Edit Command",
            groups=groups,
            command=command,
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        updated_command = Command(
            id=command.id,
            group=dialog.result["group"],
            name=dialog.result["name"],
            command=dialog.result["command"],
            parameter=dialog.result["parameter"],
            admin=dialog.result["admin"],
        )

        try:
            self.context.quick_commands_manager.update_command(
                updated_command
            )

        except ValueError as error:
            messagebox.showerror(
                "Error",
                str(error),
                parent=self,
            )
            return

        self.selected_group = updated_command.group

        self.refresh()

    def delete_command(self, command):
        confirmed = messagebox.askyesno(
            "Delete command",
            f"Delete '{command.name}'?",
            parent=self,
        )

        if not confirmed:
            return

        try:
            self.context.quick_commands_manager.remove_command(
                command
            )

        except ValueError as error:
            messagebox.showerror(
                "Error",
                str(error),
                parent=self,
            )
            return

        self.refresh()

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    def run_command(self, command: Command):
        try:
            full_command = command.command

            if command.parameter:
                full_command = (
                    f"{full_command} "
                    f"{command.parameter}"
                )

            if command.admin:
                self._run_as_admin(full_command)
            else:
                self._run_command(full_command)

        except Exception as error:
            messagebox.showerror(
                "Command error",
                str(error),
                parent=self,
            )

    def _run_command(self, command: str):
        subprocess.Popen(
            command,
            shell=True,
        )

    def _run_as_admin(self, command: str):
        import ctypes

        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "cmd.exe",
            f'/c "{command}"',
            None,
            1,
        )

        if result <= 32:
            raise RuntimeError(
                "Failed to run command as administrator."
            )


# ======================================================================
# GROUP DIALOG
# ======================================================================

class GroupDialog(ctk.CTkToplevel):
    def __init__(self, parent, title):
        super().__init__(parent)

        self.result = None

        self.title(title)
        self.geometry("400x180")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(
            0,
            weight=1,
        )

        ctk.CTkLabel(
            self,
            text="Group name",
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=25,
            pady=(25, 8),
        )

        self.entry = ctk.CTkEntry(
            self,
            placeholder_text="Development",
        )

        self.entry.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=25,
        )

        buttons = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )

        buttons.grid(
            row=2,
            column=0,
            pady=20,
        )

        ctk.CTkButton(
            buttons,
            text="Cancel",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=self.cancel,
        ).pack(
            side="left",
            padx=5,
        )

        ctk.CTkButton(
            buttons,
            text="Save",
            width=90,
            command=self.save,
        ).pack(
            side="left",
            padx=5,
        )

        self.entry.focus_set()

        self.bind(
            "<Return>",
            lambda event: self.save(),
        )

        self.bind(
            "<Escape>",
            lambda event: self.cancel(),
        )

    def save(self):
        value = self.entry.get().strip()

        if not value:
            messagebox.showwarning(
                "Invalid group",
                "Group name cannot be empty.",
                parent=self,
            )
            return

        self.result = value
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


# ======================================================================
# GROUP MENU
# ======================================================================

class GroupMenuDialog(ctk.CTkToplevel):
    def __init__(self, parent, group):
        super().__init__(parent)

        self.result = None

        self.title(group)
        self.geometry("280x150")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text=group,
            font=ctk.CTkFont(
                size=16,
                weight="bold",
            ),
        ).pack(
            pady=(20, 10),
        )

        ctk.CTkButton(
            self,
            text="Delete group",
            fg_color="transparent",
            border_width=1,
            command=self.delete,
        ).pack(
            padx=25,
            pady=5,
            fill="x",
        )

        ctk.CTkButton(
            self,
            text="Cancel",
            command=self.cancel,
        ).pack(
            padx=25,
            pady=5,
            fill="x",
        )

    def delete(self):
        self.result = "delete"
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


# ======================================================================
# COMMAND DIALOG
# ======================================================================

class CommandDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        title,
        groups,
        command=None,
        selected_group=None,
    ):
        super().__init__(parent)

        self.result = None
        self.command = command

        self.title(title)
        self.geometry("500x500")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(
            0,
            weight=1,
        )

        self._build(groups, selected_group)

    def _build(self, groups, selected_group):
        ctk.CTkLabel(
            self,
            text="Group",
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=30,
            pady=(25, 5),
        )

        current_group = (
            self.command.group
            if self.command
            else selected_group
        )

        self.group_menu = ctk.CTkOptionMenu(
            self,
            values=groups,
        )

        self.group_menu.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=30,
        )

        if current_group in groups:
            self.group_menu.set(current_group)

        # --------------------------------------------------------------

        ctk.CTkLabel(
            self,
            text="Name",
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=30,
            pady=(15, 5),
        )

        self.name_entry = ctk.CTkEntry(
            self,
            placeholder_text="VS Code",
        )

        self.name_entry.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=30,
        )

        # --------------------------------------------------------------

        ctk.CTkLabel(
            self,
            text="Command",
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=30,
            pady=(15, 5),
        )

        self.command_entry = ctk.CTkEntry(
            self,
            placeholder_text="code",
        )

        self.command_entry.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=30,
        )

        # --------------------------------------------------------------

        ctk.CTkLabel(
            self,
            text="Parameter",
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
        ).grid(
            row=6,
            column=0,
            sticky="w",
            padx=30,
            pady=(15, 5),
        )

        self.parameter_entry = ctk.CTkEntry(
            self,
            placeholder_text=".",
        )

        self.parameter_entry.grid(
            row=7,
            column=0,
            sticky="ew",
            padx=30,
        )

        # --------------------------------------------------------------

        self.admin_var = tk.BooleanVar(
            value=(
                self.command.admin
                if self.command
                else False
            )
        )

        ctk.CTkCheckBox(
            self,
            text="Run as administrator",
            variable=self.admin_var,
        ).grid(
            row=8,
            column=0,
            sticky="w",
            padx=30,
            pady=20,
        )

        # --------------------------------------------------------------
        # Buttons
        # --------------------------------------------------------------

        buttons = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )

        buttons.grid(
            row=9,
            column=0,
            pady=10,
        )

        ctk.CTkButton(
            buttons,
            text="Cancel",
            width=100,
            fg_color="transparent",
            border_width=1,
            command=self.cancel,
        ).pack(
            side="left",
            padx=5,
        )

        ctk.CTkButton(
            buttons,
            text="Save",
            width=100,
            command=self.save,
        ).pack(
            side="left",
            padx=5,
        )

        # --------------------------------------------------------------
        # Existing values
        # --------------------------------------------------------------

        if self.command:
            self.name_entry.insert(
                0,
                self.command.name,
            )

            self.command_entry.insert(
                0,
                self.command.command,
            )

            self.parameter_entry.insert(
                0,
                self.command.parameter,
            )

        self.name_entry.focus_set()

        self.bind(
            "<Escape>",
            lambda event: self.cancel(),
        )

        self.bind(
            "<Control-Return>",
            lambda event: self.save(),
        )

    def save(self):
        group = self.group_menu.get().strip()
        name = self.name_entry.get().strip()
        command = self.command_entry.get().strip()
        parameter = self.parameter_entry.get().strip()

        if not group:
            messagebox.showwarning(
                "Invalid command",
                "Group cannot be empty.",
                parent=self,
            )
            return

        if not name:
            messagebox.showwarning(
                "Invalid command",
                "Name cannot be empty.",
                parent=self,
            )
            return

        if not command:
            messagebox.showwarning(
                "Invalid command",
                "Command cannot be empty.",
                parent=self,
            )
            return

        self.result = {
            "group": group,
            "name": name,
            "command": command,
            "parameter": parameter,
            "admin": self.admin_var.get(),
        }

        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()