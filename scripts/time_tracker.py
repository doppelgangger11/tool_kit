from __future__ import annotations

import csv
import json
import os
import threading

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable


DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MAX_PROJECT_LEN = 100
STALE_HOURS = 12            # таймер дольше этого, скорее всего, забыли остановить


# ---------------------------------------------------------
# Formatting
# ---------------------------------------------------------

def format_hms(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def format_hm(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}"


def week_start(day: date) -> date:
    """Понедельник недели, в которую попадает day."""
    return day - timedelta(days=day.weekday())


def _now() -> datetime:
    return datetime.now().astimezone()


def _local(value: datetime) -> datetime:
    return value.astimezone()


# ---------------------------------------------------------
# Parsing user input (for dialogs)
# ---------------------------------------------------------

def parse_date_text(text: str) -> date:
    text = text.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d.%m.%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError("Date must look like 15.10.2026 or 2026-10-15.")


def parse_time_text(text: str):
    text = text.strip().replace(".", ":")
    try:
        return datetime.strptime(text, "%H:%M").time()
    except ValueError:
        raise ValueError("Time must look like 09:30.") from None


def last_occurrence(clock_time, now: datetime, not_before: datetime) -> datetime:
    """
    Последний момент не позже now с таким временем суток.
    Для "остановить в 18:30", когда таймер забыли выключить вечером.
    """
    candidate = datetime.combine(now.date(), clock_time, tzinfo=now.tzinfo)

    if candidate > now:
        candidate -= timedelta(days=1)

    if candidate < not_before:
        raise ValueError("That time is earlier than the timer start.")

    return candidate


# ---------------------------------------------------------
# Tracker
# ---------------------------------------------------------

class TimeTracker:
    """
    Файл JSON - источник правды: каждый вызов сверяется с файлом
    (перечитывается только если файл изменился). Поэтому окно и
    горячая клавиша всегда видят одно и то же состояние.
    """

    def __init__(self, path, clock: Callable[[], datetime] | None = None):
        self.path = Path(path)
        self._clock = clock or _now
        self._lock = threading.RLock()
        self._data: dict | None = None
        self._stamp = None

    # ---- storage ----

    @staticmethod
    def _empty() -> dict:
        return {"running": None, "entries": [], "next_id": 1, "last_project": ""}

    def _load(self) -> dict:
        try:
            info = self.path.stat()
            stamp = (info.st_mtime_ns, info.st_size)
        except OSError:
            stamp = None

        if self._data is not None and stamp == self._stamp:
            return self._data

        data = self._empty()

        if stamp is not None:
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(loaded, dict):
                    raise ValueError("root must be an object")
                data.update({k: loaded[k] for k in data if k in loaded})
                if not isinstance(data["entries"], list):
                    data["entries"] = []
            except (OSError, ValueError):
                # битый файл не затираем молча: сохраняем копию
                try:
                    backup = self.path.with_name(self.path.name + ".bak")
                    backup.write_bytes(self.path.read_bytes())
                except OSError:
                    pass

        self._data, self._stamp = data, stamp
        return data

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, self.path)

        info = self.path.stat()
        self._stamp = (info.st_mtime_ns, info.st_size)

    @staticmethod
    def _clean_project(project: str) -> str:
        project = " ".join(str(project).split())
        if not project:
            raise ValueError("Enter a project name.")
        if len(project) > MAX_PROJECT_LEN:
            raise ValueError(f"Project name is too long (max {MAX_PROJECT_LEN}).")
        return project

    def _canonical(self, data: dict, project: str) -> str:
        """'air astana' -> 'Air Astana', если такой проект уже есть (первое написание)."""
        key = project.casefold()
        names = [data["running"]["project"]] if data.get("running") else []
        names += [e.get("project", "") for e in data["entries"]]

        for name in names:
            if name.casefold() == key:
                return name

        return project

    # ---- timer ----

    def running(self) -> dict | None:
        """{'project', 'started' (datetime), 'note'} или None."""
        with self._lock:
            run = self._load()["running"]
            if not run:
                return None
            return {
                "project": run["project"],
                "started": datetime.fromisoformat(run["started"]),
                "note": run.get("note", ""),
            }

    def last_project(self) -> str:
        with self._lock:
            return self._load().get("last_project", "")

    def is_stale(self) -> bool:
        run = self.running()
        if not run:
            return False
        return (self._clock() - run["started"]).total_seconds() > STALE_HOURS * 3600

    def start(self, project: str, note: str = "", at: datetime | None = None):
        """
        Запускает таймер. Если шёл другой проект, он останавливается в тот же
        момент. Возвращает остановленную запись или None.
        """
        with self._lock:
            data = self._load()
            project = self._canonical(data, self._clean_project(project))
            now = at or self._clock()

            current = data["running"]
            if current and current["project"] == project:
                raise ValueError(f"'{project}' is already running.")

            stopped = self._stop_locked(now) if current else None

            data["running"] = {
                "project": project,
                "started": now.isoformat(timespec="seconds"),
                "note": note.strip(),
            }
            data["last_project"] = project
            self._save()
            return stopped

    def _stop_locked(self, at: datetime):
        data = self._data
        run = data["running"]
        if not run:
            return None

        started = datetime.fromisoformat(run["started"])
        end = max(at, started)              # не уходим в минус

        if (end - started).total_seconds() < 1:
            data["running"] = None          # случайный двойной клик: запись не нужна
            return None

        entry = {
            "id": data["next_id"],
            "project": run["project"],
            "start": run["started"],
            "end": end.isoformat(timespec="seconds"),
            "note": run.get("note", ""),
        }
        data["next_id"] += 1
        data["entries"].append(entry)
        data["running"] = None
        return entry

    def stop(self, at: datetime | None = None):
        """Останавливает таймер. Возвращает запись или None, если он не шёл."""
        with self._lock:
            data = self._load()
            had_timer = bool(data["running"])
            entry = self._stop_locked(at or self._clock())
            if had_timer:
                self._save()
            return entry

    def toggle(self, default_project: str = "") -> str:
        """Для горячей клавиши: стоп, если идёт, иначе старт последнего проекта."""
        with self._lock:
            run = self.running()

            if run:
                entry = self.stop()
                seconds = self._duration(entry) if entry else 0
                return f"Stopped: {run['project']} ({format_hm(seconds)})"

            project = self.last_project() or default_project
            if not project:
                raise ValueError(
                    "No project yet. Pick one in the Time Tracker window first."
                )

            self.start(project)
            return f"Started: {project}"

    # ---- entries ----

    @staticmethod
    def _duration(entry: dict) -> float:
        return (
            datetime.fromisoformat(entry["end"])
            - datetime.fromisoformat(entry["start"])
        ).total_seconds()

    def add_entry(self, project: str, start: datetime, end: datetime, note: str = ""):
        with self._lock:
            if end <= start:
                raise ValueError("The end must be later than the start.")

            data = self._load()
            project = self._canonical(data, self._clean_project(project))
            entry = {
                "id": data["next_id"],
                "project": project,
                "start": start.astimezone().isoformat(timespec="seconds"),
                "end": end.astimezone().isoformat(timespec="seconds"),
                "note": note.strip(),
            }
            data["next_id"] += 1
            data["entries"].append(entry)
            data["last_project"] = data.get("last_project") or project
            self._save()
            return entry

    def delete_entry(self, entry_id: int) -> bool:
        with self._lock:
            data = self._load()
            before = len(data["entries"])
            data["entries"] = [e for e in data["entries"] if e.get("id") != entry_id]

            if len(data["entries"]) == before:
                return False

            self._save()
            return True

    def entries(self, first: date, last: date) -> list[dict]:
        """
        Записи, начавшиеся в [first, last] (по местной дате), по времени.
        Идущий таймер добавляется как запись с running=True до текущего момента.
        """
        with self._lock:
            data = self._load()
            result = []

            for e in data["entries"]:
                try:
                    start = _local(datetime.fromisoformat(e["start"]))
                    end = _local(datetime.fromisoformat(e["end"]))
                except (KeyError, ValueError):
                    continue

                if first <= start.date() <= last:
                    result.append({
                        "id": e.get("id"), "project": e.get("project", "?"),
                        "start": start, "end": end,
                        "note": e.get("note", ""), "running": False,
                    })

            run = data["running"]
            if run:
                start = _local(datetime.fromisoformat(run["started"]))
                if first <= start.date() <= last:
                    result.append({
                        "id": None, "project": run["project"],
                        "start": start, "end": _local(self._clock()),
                        "note": run.get("note", ""), "running": True,
                    })

            return sorted(result, key=lambda e: e["start"])

    def projects(self) -> list[str]:
        with self._lock:
            data = self._load()
            names = {e.get("project", "") for e in data["entries"]}
            if data["running"]:
                names.add(data["running"]["project"])
            names.discard("")
            return sorted(names, key=str.lower)

    # ---- reports ----

    def week_summary(self, monday: date):
        """
        -> (проекты, {проект: [секунд за каждый день пн..вс]}, итог по дням)
        """
        sunday = monday + timedelta(days=6)
        table: dict[str, list[float]] = {}

        for e in self.entries(monday, sunday):
            seconds = (e["end"] - e["start"]).total_seconds()
            row = table.setdefault(e["project"], [0.0] * 7)
            row[(e["start"].date() - monday).days] += seconds

        projects = sorted(table, key=str.lower)
        totals = [sum(table[p][d] for p in projects) for d in range(7)]

        return projects, table, totals

    def export_summary_csv(self, path, monday: date, excel_ru: bool = True) -> None:
        projects, table, totals = self.week_summary(monday)
        delimiter, fmt = _csv_style(excel_ru)

        header = ["Project"] + [
            f"{DAY_NAMES[i]} {(monday + timedelta(days=i)):%d.%m}" for i in range(7)
        ] + ["Total (h)"]

        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=delimiter)
            writer.writerow(header)

            for project in projects:
                row = table[project]
                writer.writerow(
                    [project] + [fmt(s) for s in row] + [fmt(sum(row))]
                )

            writer.writerow(
                ["TOTAL"] + [fmt(s) for s in totals] + [fmt(sum(totals))]
            )

    def export_entries_csv(self, path, first: date, last: date, excel_ru: bool = True) -> None:
        delimiter, fmt = _csv_style(excel_ru)

        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=delimiter)
            writer.writerow(
                ["Date", "Project", "Start", "End", "Hours", "Note"]
            )

            for e in self.entries(first, last):
                seconds = (e["end"] - e["start"]).total_seconds()
                writer.writerow([
                    f"{e['start']:%d.%m.%Y}", e["project"],
                    f"{e['start']:%H:%M}", f"{e['end']:%H:%M}",
                    fmt(seconds), e["note"],
                ])


def _csv_style(excel_ru: bool):
    """
    Русский Excel открывает CSV с разделителем ';' и десятичной запятой.
    Без этого всё склеивается в одну колонку, а числа становятся текстом.
    """
    if excel_ru:
        return ";", lambda s: f"{s / 3600:.2f}".replace(".", ",")
    return ",", lambda s: f"{s / 3600:.2f}"


# ---------------------------------------------------------
# Shared instance (окно и горячая клавиша используют один объект)
# ---------------------------------------------------------

_trackers: dict[str, TimeTracker] = {}


def get_tracker(base_dir) -> TimeTracker:
    path = Path(base_dir) / "db" / "time_log.json"
    key = str(path.resolve())

    if key not in _trackers:
        _trackers[key] = TimeTracker(path)

    return _trackers[key]
