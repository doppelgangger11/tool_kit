import customtkinter as ctk

from interface.view import View


class DashboardView(View):
    def build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_stats()
        self._build_actions()

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _build_header(self):
        frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        frame.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=30,
            pady=(30, 10),
        )

        ctk.CTkLabel(
            frame,
            text="Dashboard",
            font=ctk.CTkFont(
                size=28,
                weight="bold",
            ),
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame,
            text="Welcome back to Toolkit.",
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=14),
        ).pack(
            anchor="w",
            pady=(5, 0),
        )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def _build_stats(self):
        frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=30,
            pady=10,
        )

        for column in range(3):
            frame.grid_columnconfigure(
                column,
                weight=1,
            )

        self.notes_card = self._create_stat_card(
            frame,
            column=0,
            title="Notes",
            value="0",
            subtitle="Saved notes",
        )

        self.pinned_card = self._create_stat_card(
            frame,
            column=1,
            title="Pinned",
            value="0",
            subtitle="Pinned notes",
        )

        self.commands_card = self._create_stat_card(
            frame,
            column=2,
            title="Commands",
            value="0",
            subtitle="Quick commands",
        )

    def _create_stat_card(
        self,
        parent,
        column: int,
        title: str,
        value: str,
        subtitle: str,
    ):
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
        )

        card.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=6,
        )

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            text_color=("gray40", "gray70"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(15, 0),
        )

        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(
                size=26,
                weight="bold",
            ),
        )

        value_label.pack(
            anchor="w",
            padx=18,
            pady=(5, 0),
        )

        ctk.CTkLabel(
            card,
            text=subtitle,
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(0, 15),
        )

        return value_label

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _build_actions(self):
        container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
        )

        container.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=24,
            pady=(10, 20),
        )

        container.grid_columnconfigure(
            0,
            weight=1,
        )
        container.grid_columnconfigure(
            1,
            weight=1,
        )

        # --------------------------------------------------------------
        # Work
        # --------------------------------------------------------------

        self._create_section_title(
            container,
            row=0,
            text="Work",
        )

        self._create_action_card(
            container,
            row=1,
            column=0,
            title="🚀  Launcher",
            description="Launch your configured work setup.",
            command=lambda: self.app.show("launcher"),
        )

        self._create_action_card(
            container,
            row=1,
            column=1,
            title="⚡  New Task",
            description="Create and activate a new task.",
            command=lambda: self.app.show("activation"),
        )

        # --------------------------------------------------------------
        # Tools
        # --------------------------------------------------------------

        self._create_section_title(
            container,
            row=2,
            text="Tools",
        )

        self._create_action_card(
            container,
            row=3,
            column=0,
            title="📝  Quick Notes",
            description="Open your notes.",
            command=lambda: self.app.show("notes"),
        )

        self._create_action_card(
            container,
            row=3,
            column=1,
            title="⌨  Quick Commands",
            description="Run your frequently used commands.",
            command=lambda: self.app.show("commands"),
        )

        # --------------------------------------------------------------
        # Games
        # --------------------------------------------------------------

        self._create_section_title(
            container,
            row=4,
            text="Games",
        )

        self._create_action_card(
            container,
            row=5,
            column=0,
            title="♟  Chess",
            description="Play chess against the bot.",
            command=lambda: self.app.show("chess"),
        )

        self._create_action_card(
            container,
            row=5,
            column=1,
            title="💣  Minesweeper",
            description="Play Minesweeper.",
            command=lambda: self.app.show("minesweeper"),
        )

        self._create_action_card(
            container,
            row=6,
            column=0,
            title="⭕  Tic-Tac-Toe",
            description="Play Tic-Tac-Toe.",
            command=lambda: self.app.show("tic_tac_toe"),
        )

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def _create_section_title(
        self,
        parent,
        row: int,
        text: str,
    ):
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(
                size=16,
                weight="bold",
            ),
        ).grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=6,
            pady=(20, 8),
        )

    def _create_action_card(
        self,
        parent,
        row: int,
        column: int,
        title: str,
        description: str,
        command,
    ):
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
        )

        card.grid(
            row=row,
            column=column,
            sticky="nsew",
            padx=6,
            pady=6,
        )

        card.grid_columnconfigure(
            0,
            weight=1,
        )

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(
                size=15,
                weight="bold",
            ),
            anchor="w",
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=18,
            pady=(15, 3),
        )

        ctk.CTkLabel(
            card,
            text=description,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
            anchor="w",
            justify="left",
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 12),
        )

        ctk.CTkButton(
            card,
            text="Open",
            width=100,
            command=command,
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=18,
            pady=(0, 15),
        )

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def on_show(self):
        self._refresh_statistics()

    def _refresh_statistics(self):
        notes = self.context.notes_manager.notes

        pinned = [
            note
            for note in notes
            if note.pinned
        ]

        commands = self.context.quick_commands_manager.get_commands()

        self.notes_card.configure(
            text=str(len(notes))
        )

        self.pinned_card.configure(
            text=str(len(pinned))
        )

        self.commands_card.configure(
            text=str(len(commands))
        )