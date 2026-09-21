import subprocess
import tkinter as tk

from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from scripts.quick_commands_manager import (
    QuickCommandsManager,
    Command,
)


def open_quick_commands(
    root,
    base_dir,
    base_settings
):
    QuickCommandsWindow(
        root,
        base_dir,
        base_settings
    )


class QuickCommandsWindow:

    def __init__(
        self,
        root,
        base_dir,
        base_settings
    ):

        self.root = root
        self.base_dir = Path(base_dir)
        self.base_settings = base_settings

        self.manager = QuickCommandsManager(
            self.base_dir
            / "db"
            / "quick_commands.ini"
        )

        self.commands = self.manager.get_commands()

        # -----------------------------------------------------
        # CURRENT DIRECTORY
        # -----------------------------------------------------

        self.current_directory = Path(
            self.base_settings["DIRS"]["working_dir"]
        ).resolve()

        self.window = tk.Toplevel(root)

        self.window.title(
            "Quick Commands"
        )

        self.window.geometry(
            "850x650"
        )

        self.window.minsize(
            700,
            500
        )

        self._build_interface()
        self._refresh()

    # =========================================================
    # INTERFACE
    # =========================================================

    def _build_interface(self):

        # -----------------------------------------------------
        # DIRECTORY
        # -----------------------------------------------------

        directory_frame = ttk.LabelFrame(
            self.window,
            text="Working directory"
        )

        directory_frame.pack(
            fill="x",
            padx=10,
            pady=10
        )

        self.directory_var = tk.StringVar(
            value=str(
                self.current_directory
            )
        )

        self.directory_entry = ttk.Entry(
            directory_frame,
            textvariable=self.directory_var
        )

        self.directory_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=5,
            pady=5
        )

        ttk.Button(
            directory_frame,
            text="📁",
            width=4,
            command=self._select_directory
        ).pack(
            side="left",
            padx=(0, 5)
        )

        ttk.Button(
            directory_frame,
            text="↩",
            width=4,
            command=self._reset_directory
        ).pack(
            side="left",
            padx=(0, 5)
        )

        # -----------------------------------------------------
        # ACTIONS
        # -----------------------------------------------------

        actions_frame = ttk.Frame(
            self.window
        )

        actions_frame.pack(
            fill="x",
            padx=10,
            pady=(0, 5)
        )

        ttk.Button(
            actions_frame,
            text="+ Создать группу",
            command=self._create_group
        ).pack(
            side="left"
        )

        ttk.Button(
            actions_frame,
            text="CMD",
            command=self._open_cmd
        ).pack(
            side="left",
            padx=(10, 0)
        )

        ttk.Button(
            actions_frame,
            text="PowerShell",
            command=self._open_powershell
        ).pack(
            side="left",
            padx=(5, 0)
        )

        ttk.Button(
            actions_frame,
            text="Explorer",
            command=self._open_explorer
        ).pack(
            side="left",
            padx=(5, 0)
        )

        # -----------------------------------------------------
        # SCROLLABLE AREA
        # -----------------------------------------------------

        container = ttk.Frame(
            self.window
        )

        container.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        self.canvas = tk.Canvas(
            container,
            highlightthickness=0
        )

        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=self.canvas.yview
        )

        self.groups_frame = ttk.Frame(
            self.canvas
        )

        self.groups_frame.bind(
            "<Configure>",
            lambda event: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window(
            (0, 0),
            window=self.groups_frame,
            anchor="nw"
        )

        self.canvas.configure(
            yscrollcommand=scrollbar.set
        )

        self.canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

    # =========================================================
    # DIRECTORY
    # =========================================================

    def _select_directory(self):

        directory = filedialog.askdirectory(
            parent=self.window,
            initialdir=str(
                self.current_directory
            )
        )

        if not directory:
            return

        self.current_directory = Path(
            directory
        ).resolve()

        self.directory_var.set(
            str(self.current_directory)
        )

    def _reset_directory(self):

        self.current_directory = Path(
            self.base_settings["DIRS"]["working_dir"]
        ).resolve()

        self.directory_var.set(
            str(self.current_directory)
        )

    def _get_current_directory(self):

        directory = Path(
            self.directory_var.get()
        ).expanduser()

        if not directory.exists():

            messagebox.showerror(
                "Ошибка",
                "Рабочая директория не существует.",
                parent=self.window
            )

            return None

        if not directory.is_dir():

            messagebox.showerror(
                "Ошибка",
                "Указанный путь не является директорией.",
                parent=self.window
            )

            return None

        self.current_directory = directory.resolve()

        self.directory_var.set(
            str(self.current_directory)
        )

        return self.current_directory

    # =========================================================
    # REFRESH
    # =========================================================

    def _refresh(self):

        self.commands = (
            self.manager.get_commands()
        )

        for widget in self.groups_frame.winfo_children():
            widget.destroy()

        groups = self.manager.get_groups()

        if not groups:

            ttk.Label(
                self.groups_frame,
                text="Нет созданных групп."
            ).pack(
                pady=30
            )

            return

        for group in groups:
            self._create_group_widget(
                group
            )

    # =========================================================
    # GROUP
    # =========================================================

    def _create_group_widget(
        self,
        group
    ):

        frame = ttk.LabelFrame(
            self.groups_frame,
            text=group
        )

        frame.pack(
            fill="x",
            pady=5
        )

        header = ttk.Frame(
            frame
        )

        header.pack(
            fill="x",
            padx=5,
            pady=5
        )

        ttk.Button(
            header,
            text="+ Команда",
            command=lambda g=group:
                self._create_command(g)
        ).pack(
            side="right"
        )

        ttk.Button(
            header,
            text="Удалить группу",
            command=lambda g=group:
                self._delete_group(g)
        ).pack(
            side="right",
            padx=(0, 5)
        )

        group_commands = [
            command
            for command in self.commands
            if command.group == group
        ]

        if not group_commands:

            ttk.Label(
                frame,
                text="Нет команд."
            ).pack(
                anchor="w",
                padx=10,
                pady=(0, 8)
            )

            return

        for command in group_commands:

            self._create_command_row(
                frame,
                command
            )

    # =========================================================
    # COMMAND ROW
    # =========================================================

    def _create_command_row(
        self,
        parent,
        command
    ):

        row = ttk.Frame(
            parent
        )

        row.pack(
            fill="x",
            padx=5,
            pady=2
        )

        execute_button = ttk.Button(
            row,
            text=command.name,
            command=lambda c=command:
                self._execute_command(c)
        )

        execute_button.pack(
            side="left",
            fill="x",
            expand=True
        )

        ttk.Button(
            row,
            text="✎",
            width=3,
            command=lambda c=command:
                self._edit_command(c)
        ).pack(
            side="left",
            padx=(5, 0)
        )

        ttk.Button(
            row,
            text="×",
            width=3,
            command=lambda c=command:
                self._delete_command(c)
        ).pack(
            side="left",
            padx=(3, 0)
        )

    # =========================================================
    # GROUP CREATION
    # =========================================================

    def _create_group(self):

        window = tk.Toplevel(
            self.window
        )

        window.title(
            "Создать группу"
        )

        window.geometry(
            "350x130"
        )

        window.resizable(
            False,
            False
        )

        window.transient(
            self.window
        )

        window.grab_set()

        frame = ttk.Frame(
            window
        )

        frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=15
        )

        ttk.Label(
            frame,
            text="Название группы:"
        ).pack(
            anchor="w"
        )

        name_var = tk.StringVar()

        entry = ttk.Entry(
            frame,
            textvariable=name_var
        )

        entry.pack(
            fill="x",
            pady=(5, 10)
        )

        entry.focus()

        def save():

            name = name_var.get().strip()

            if not name:
                return

            try:
                self.manager.add_group(
                    name
                )

            except ValueError as error:

                messagebox.showwarning(
                    "Ошибка",
                    str(error),
                    parent=window
                )

                return

            window.destroy()
            self._refresh()

        ttk.Button(
            frame,
            text="Создать",
            command=save
        ).pack(
            side="right"
        )

        ttk.Button(
            frame,
            text="Отмена",
            command=window.destroy
        ).pack(
            side="right",
            padx=(0, 5)
        )

    def _delete_group(
        self,
        group
    ):

        result = messagebox.askyesno(
            "Удаление группы",
            (
                f"Удалить группу '{group}'?\n\n"
                "Все команды этой группы "
                "также будут удалены."
            ),
            parent=self.window
        )

        if not result:
            return

        self.manager.remove_group(
            group
        )

        self._refresh()

    # =========================================================
    # COMMAND EDITOR
    # =========================================================

    def _create_command(
        self,
        group
    ):

        self._open_command_editor(
            group=group
        )

    def _edit_command(
        self,
        command
    ):

        self._open_command_editor(
            command=command
        )

    def _open_command_editor(
        self,
        group=None,
        command=None
    ):

        editor = tk.Toplevel(
            self.window
        )

        editor.title(
            "Редактирование команды"
            if command
            else "Создание команды"
        )

        editor.geometry(
            "550x400"
        )

        editor.minsize(
            500,
            350
        )

        editor.transient(
            self.window
        )

        editor.grab_set()

        frame = ttk.Frame(
            editor
        )

        frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=15
        )

        # -----------------------------------------------------
        # NAME
        # -----------------------------------------------------

        ttk.Label(
            frame,
            text="Название:"
        ).pack(
            anchor="w"
        )

        name_var = tk.StringVar(
            value=command.name
            if command
            else ""
        )

        ttk.Entry(
            frame,
            textvariable=name_var
        ).pack(
            fill="x",
            pady=(3, 10)
        )

        # -----------------------------------------------------
        # COMMAND
        # -----------------------------------------------------

        ttk.Label(
            frame,
            text="Команда:"
        ).pack(
            anchor="w"
        )

        command_var = tk.StringVar(
            value=command.command
            if command
            else ""
        )

        ttk.Entry(
            frame,
            textvariable=command_var
        ).pack(
            fill="x",
            pady=(3, 10)
        )

        # -----------------------------------------------------
        # PARAMETER
        # -----------------------------------------------------

        parameter_var = tk.BooleanVar(
            value=bool(
                command.parameter
            )
            if command
            else False
        )

        ttk.Checkbutton(
            frame,
            text="Запрашивать параметр перед выполнением",
            variable=parameter_var
        ).pack(
            anchor="w",
            pady=5
        )

        # -----------------------------------------------------
        # ADMIN
        # -----------------------------------------------------

        admin_var = tk.BooleanVar(
            value=command.admin
            if command
            else False
        )

        ttk.Checkbutton(
            frame,
            text="Требуются права администратора",
            variable=admin_var
        ).pack(
            anchor="w",
            pady=5
        )

        # -----------------------------------------------------
        # BUTTONS
        # -----------------------------------------------------

        buttons = ttk.Frame(
            frame
        )

        buttons.pack(
            side="bottom",
            fill="x",
            pady=(15, 0)
        )

        ttk.Button(
            buttons,
            text="Сохранить",
            command=lambda:
                self._save_command(
                    editor,
                    group
                    if group
                    else command.group,
                    command,
                    name_var.get(),
                    command_var.get(),
                    parameter_var.get(),
                    admin_var.get()
                )
        ).pack(
            side="right"
        )

        ttk.Button(
            buttons,
            text="Отмена",
            command=editor.destroy
        ).pack(
            side="right",
            padx=(0, 5)
        )

    # =========================================================
    # COMMAND SAVE
    # =========================================================

    def _save_command(
        self,
        editor,
        group,
        command,
        name,
        command_text,
        has_parameter,
        admin
    ):

        name = name.strip()
        command_text = command_text.strip()

        if not name:

            messagebox.showwarning(
                "Ошибка",
                "Введите название команды.",
                parent=editor
            )

            return

        if not command_text:

            messagebox.showwarning(
                "Ошибка",
                "Введите команду.",
                parent=editor
            )

            return

        parameter = (
            "input"
            if has_parameter
            else ""
        )

        if command:

            command.name = name
            command.command = command_text
            command.parameter = parameter
            command.admin = admin

            try:

                self.manager.update_command(
                    command
                )

            except ValueError as error:

                messagebox.showerror(
                    "Ошибка",
                    str(error),
                    parent=editor
                )

                return

        else:

            try:

                self.manager.add_command(
                    group=group,
                    name=name,
                    command=command_text,
                    parameter=parameter,
                    admin=admin
                )

            except ValueError as error:

                messagebox.showerror(
                    "Ошибка",
                    str(error),
                    parent=editor
                )

                return

        editor.destroy()

        self._refresh()

    # =========================================================
    # COMMAND DELETE
    # =========================================================

    def _delete_command(
        self,
        command
    ):

        result = messagebox.askyesno(
            "Удаление команды",
            f"Удалить '{command.name}'?",
            parent=self.window
        )

        if not result:
            return

        self.manager.remove_command(
            command
        )

        self._refresh()

    # =========================================================
    # EXECUTION
    # =========================================================

    def _execute_command(
        self,
        command
    ):

        directory = (
            self._get_current_directory()
        )

        if directory is None:
            return

        parameter = None

        if command.parameter == "input":

            parameter = self._ask_parameter(
                command
            )

            if parameter is None:
                return

        command_text = command.command

        if parameter is not None:

            try:

                command_text = command_text.format(
                    parameter
                )

            except (IndexError, KeyError, ValueError):

                messagebox.showerror(
                    "Ошибка",
                    "Не удалось подставить параметр.",
                    parent=self.window
                )

                return

        try:

            subprocess.Popen(
                command_text,
                cwd=directory,
                shell=True
            )

        except Exception as error:

            messagebox.showerror(
                "Ошибка выполнения",
                str(error),
                parent=self.window
            )

    # =========================================================
    # PARAMETER WINDOW
    # =========================================================

    def _ask_parameter(
        self,
        command
    ):

        window = tk.Toplevel(
            self.window
        )

        window.title(
            command.name
        )

        window.geometry(
            "450x180"
        )

        window.resizable(
            False,
            False
        )

        window.transient(
            self.window
        )

        window.grab_set()

        result = {
            "value": None
        }

        frame = ttk.Frame(
            window
        )

        frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=15
        )

        ttk.Label(
            frame,
            text=command.name
        ).pack(
            pady=(0, 10)
        )

        value_var = tk.StringVar()

        entry = ttk.Entry(
            frame,
            textvariable=value_var
        )

        entry.pack(
            fill="x"
        )

        entry.focus()

        def execute():

            result["value"] = value_var.get()

            window.destroy()

        def cancel():

            window.destroy()

        buttons = ttk.Frame(
            frame
        )

        buttons.pack(
            side="bottom",
            fill="x",
            pady=(15, 0)
        )

        ttk.Button(
            buttons,
            text="Выполнить",
            command=execute
        ).pack(
            side="right"
        )

        ttk.Button(
            buttons,
            text="Отмена",
            command=cancel
        ).pack(
            side="right",
            padx=(0, 5)
        )

        self.window.wait_window(
            window
        )

        return result["value"]

    # =========================================================
    # QUICK ACTIONS
    # =========================================================

    def _open_cmd(self):

        directory = (
            self._get_current_directory()
        )

        if directory is None:
            return

        subprocess.Popen(
            ["cmd.exe"],
            cwd=directory
        )

    def _open_powershell(self):

        directory = (
            self._get_current_directory()
        )

        if directory is None:
            return

        subprocess.Popen(
            [
                "powershell.exe"
            ],
            cwd=directory
        )

    def _open_explorer(self):

        directory = (
            self._get_current_directory()
        )

        if directory is None:
            return

        subprocess.Popen(
            [
                "explorer.exe",
                str(directory)
            ]
        )