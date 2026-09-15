import json
from datetime import datetime


class Note:
    def __init__(
        self,
        id: int,
        theme: str,
        note: str,
        date: datetime | None = None
    ):
        self.id = id
        self.theme = theme
        self.note = note
        self.date = date or datetime.now().replace(microsecond=0)

    def to_dict(self):
        return {
            'id': self.id,
            'theme': self.theme,
            'date': self.date.strftime('%Y-%m-%d %H:%M:%S'),
            'note': self.note
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=int(data['id']),
            theme=data['theme'],
            note=data['note'],
            date=datetime.strptime(
                data['date'],
                '%Y-%m-%d %H:%M:%S'
            )
        )


class NotesManager:

    def __init__(self, path='../db/notes.json'):
        self.path = path
        self.notes = []

    def read_notes(self):
        with open(
            self.path,
            'r',
            encoding='utf-8'
        ) as file:
            data = json.load(file)

        self.notes = [
            Note.from_dict(note)
            for note in data
        ]

        return self.notes

    def write_notes(self):
        with open(
            self.path,
            'w',
            encoding='utf-8'
        ) as file:
            json.dump(
                [note.to_dict() for note in self.notes],
                file,
                ensure_ascii=False,
                indent=4
            )

    def create_note(self, theme, note):
        new_note = Note(
            id=self.get_next_id(),
            theme=theme,
            note=note
        )

        self.notes.append(new_note)

        return new_note

    def get_next_id(self):
        if not self.notes:
            return 0

        return max(
            note.id
            for note in self.notes
        ) + 1

    def delete(self, note_id):
        self.notes = [
            note
            for note in self.notes
            if note.id != note_id
        ]