import customtkinter as ctk

from interface.view import View


class NotesView(View):

    def build(self):
        self.title = ctk.CTkLabel(
            self,
            text="Quick Notes",
            font=("Arial", 26, "bold"),
        )
        self.title.pack(
            padx=30,
            pady=(30, 20),
            anchor="w",
        )

        self.notes_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
        )
        self.notes_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=10,
        )

    def on_show(self):
        self.refresh()

    def refresh(self):
        for widget in self.notes_frame.winfo_children():
            widget.destroy()

        notes = self.context.notes_manager.notes

        notes = sorted(
            notes,
            key=lambda note: (
                not note.pinned,
                note.date,
            ),
        )

        for note in notes:
            self.create_note_card(note)

    def create_note_card(self, note):
        card = ctk.CTkFrame(
            self.notes_frame,
        )

        card.pack(
            fill="x",
            padx=10,
            pady=5,
        )

        ctk.CTkLabel(
            card,
            text=(
                f"📌 {note.theme}"
                if note.pinned
                else note.theme
            ),
            font=("Arial", 15, "bold"),
            anchor="w",
        ).pack(
            fill="x",
            padx=15,
            pady=(10, 3),
        )

        ctk.CTkLabel(
            card,
            text=note.note,
            anchor="w",
            justify="left",
        ).pack(
            fill="x",
            padx=15,
            pady=3,
        )

        ctk.CTkLabel(
            card,
            text=note.date.strftime(
                "%Y-%m-%d %H:%M"
            ),
            anchor="w",
        ).pack(
            padx=15,
            pady=(3, 10),
            anchor="w",
        )