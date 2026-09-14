from pathlib import Path
import os


PROGRAM_LOCATIONS = [
    Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs",
    Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"),
]


def get_programs() -> dict[str, Path]:
    programs = {}

    for location in PROGRAM_LOCATIONS:
        if not location.exists():
            continue

        for file in location.rglob("*.lnk"):
            programs[file.stem] = file

    return dict(sorted(programs.items()))


def launch_selected_programs(settings: dict) -> None:
    programs = get_programs()

    for name, enabled in settings.get("PROGRAMS", {}).items():

        if not enabled:
            continue

        program = programs.get(name)

        if program is not None:
            os.startfile(program)