import json
import os
import re

from pathlib import Path
from typing import NamedTuple


# tool_kit/ (scripts/program_launcher.py -> на два уровня вверх)
BASE_DIR = Path(__file__).resolve().parent.parent

PROGRAM_LOCATIONS = [
    Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs",
    Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"),
]


CUSTOM_DIR = BASE_DIR / "db" / "programs"
CUSTOM_FILE = BASE_DIR / "db" / "custom_programs.json"
CUSTOM_EXTENSIONS = {".lnk", ".exe", ".bat", ".cmd", ".url"}

_URI = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]+:")


class Program(NamedTuple):
    target: str
    args: str = ""
    source: str = "start_menu"  # start_menu | folder | custom


# ---------------------------------------------------------
# Custom programs registry
# ---------------------------------------------------------

def is_uri(target: str) -> bool:
    return bool(_URI.match(target.strip()))


def load_custom_programs() -> dict[str, dict]:
    try:
        data = json.loads(CUSTOM_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

    if not isinstance(data, dict):
        return {}

    result = {}
    for name, item in data.items():
        if isinstance(item, dict) and str(item.get("target", "")).strip():
            result[str(name)] = {
                "target": str(item["target"]).strip(),
                "args": str(item.get("args", "") or "").strip(),
            }

    return result


def _save_custom_programs(data: dict[str, dict]) -> None:
    CUSTOM_FILE.parent.mkdir(parents=True, exist_ok=True)

    tmp = CUSTOM_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(CUSTOM_FILE)


def validate_custom_program(name: str, target: str) -> str | None:
    """Возвращает текст ошибки или None."""
    name = name.strip()
    target = target.strip()

    if not name:
        return "Enter program name."

    # имя попадает в settings.ini как ключ
    if any(c in name for c in "=\r\n") or name[0] in "#;[":
        return "Name cannot contain '=' or start with # ; [ "

    if not target:
        return "Enter a file path or a URI (for example ms-teams:)."

    if not is_uri(target):
        expanded = Path(os.path.expandvars(target))
        if not expanded.exists():
            return f"File not found: {expanded}"

    return None


def add_custom_program(name: str, target: str, args: str = "") -> None:
    error = validate_custom_program(name, target)
    if error:
        raise ValueError(error)

    data = load_custom_programs()
    data[name.strip()] = {"target": target.strip(), "args": args.strip()}
    _save_custom_programs(data)


def remove_custom_program(name: str) -> None:
    data = load_custom_programs()
    if data.pop(name, None) is not None:
        _save_custom_programs(data)


# ---------------------------------------------------------
# Discovery / launch
# ---------------------------------------------------------

def get_programs() -> dict[str, Program]:
    programs: dict[str, Program] = {}

    for location in PROGRAM_LOCATIONS:
        if not location.exists():
            continue

        try:
            for file in location.rglob("*.lnk"):
                programs[file.stem] = Program(str(file), source="start_menu")
        except OSError:
            continue

    if CUSTOM_DIR.is_dir():
        try:
            for file in sorted(CUSTOM_DIR.iterdir()):
                if file.is_file() and file.suffix.lower() in CUSTOM_EXTENSIONS:
                    programs[file.stem] = Program(str(file), source="folder")
        except OSError:
            pass

    for name, item in load_custom_programs().items():
        programs[name] = Program(item["target"], item["args"], "custom")

    return dict(sorted(programs.items(), key=lambda pair: pair[0].lower()))


def launch_program(program: Program) -> None:
    target = os.path.expandvars(program.target)

    if program.args:
        os.startfile(target, arguments=os.path.expandvars(program.args))
    else:
        os.startfile(target)


def launch_selected_programs(settings: dict) -> list[str]:
    programs = get_programs()
    problems = []

    for name, enabled in settings.get("PROGRAMS", {}).items():

        if not enabled:
            continue

        program = programs.get(name)

        if program is None:
            problems.append(f"{name}: not found")
            continue

        try:
            launch_program(program)
        except (OSError, AttributeError) as error:
            problems.append(f"{name}: {error}")

    for problem in problems:
        print(f"[Launcher] {problem}")

    return problems