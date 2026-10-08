import copy
import json
import os
import re
import shutil

from configparser import ConfigParser, Error as ConfigError
from pathlib import Path
from typing import Any


SETTINGS_FILE = "settings.ini"
TEMPLATES_DIR_NAME = "templates"

# Values for a NEW installation. An existing settings.ini is not changed,
# missing keys are simply filled in from here.
DEFAULTS: dict[str, dict[str, Any]] = {
    "BASE": {
        "log": False,
        "hotkey": "ctrl+space",   # launcher; "off" - disable
    },
    "DIRS": {
        "working_dir": "./workspace",   # relative to the folder with main.py
        "temp_dir": "/temp",            # inside working_dir
        "notes_dir": "./db",
    },
    "PROGRAMS": {},
    "ARCHITECTURE": {
        "activation_dir": "active",
        "active": "./active",           # inside working_dir
        "tests": "./tests",
        "complete": "./complete",
    },
}

EXAMPLE_TEMPLATE = {
    "name": "Empty",
    "dirs": ["$active_folder$/$name_of_project$/"],
    "copy_from_temp": {"is_copy": False, "dirs": []},
    "files": [],
}


# ---------------------------------------------------------
# ini read / write
# ---------------------------------------------------------

def _new_parser() -> ConfigParser:
    # interpolation=None: the % character in values (e.g. %APPDATA%) does not break reading
    # delimiters=("=",): a colon in a program name is not treated as a delimiter
    config = ConfigParser(interpolation=None, delimiters=("=",))
    config.optionxform = str  # keep the case of keys
    return config


_INT = re.compile(r"[+-]?(0|[1-9]\d*)")
_FLOAT = re.compile(r"[+-]?\d+\.\d+")


def _convert(value: str) -> Any:
    v = value.strip()

    if _INT.fullmatch(v):
        return int(v)

    if _FLOAT.fullmatch(v):
        return float(v)

    low = v.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False

    return value


def read_settings(directory: Path) -> dict[str, dict[str, Any]]:
    """
    Always returns the full set of settings:
    values from settings.ini on top of DEFAULTS, nothing fails with KeyError.
    """
    directory = Path(directory)
    path = directory / SETTINGS_FILE
    settings = copy.deepcopy(DEFAULTS)

    if not path.is_file():
        print(f"[Settings] {path} not found, creating with defaults")
        _try_write(directory, settings)
        return settings

    config = _new_parser()

    try:
        with path.open("r", encoding="utf-8-sig") as file:
            config.read_file(file)

    except (ConfigError, UnicodeDecodeError, OSError) as error:
        backup = path.with_name(SETTINGS_FILE + ".bak")
        print(f"[Settings] {path} is broken ({error}), backup: {backup}")
        try:
            shutil.copy2(path, backup)
        except OSError:
            pass
        _try_write(directory, settings)
        return settings

    for section in config.sections():
        target = settings.setdefault(section, {})
        for key, value in config[section].items():
            target[key] = _convert(value)

    return settings


def write_settings(
    directory: Path,
    settings: dict[str, dict[str, Any]],
) -> None:
    directory = Path(directory)

    config = _new_parser()
    for section, values in settings.items():
        config[section] = {str(k): str(v) for k, v in values.items()}

    path = directory / SETTINGS_FILE
    tmp = path.with_name(SETTINGS_FILE + ".tmp")

    # write to a temporary file and swap it in, so a failure cannot leave a truncated ini
    with tmp.open("w", encoding="utf-8") as file:
        config.write(file)

    os.replace(tmp, path)


def _try_write(directory: Path, settings) -> None:
    try:
        write_settings(directory, settings)
    except OSError as error:
        print(f"[Settings] Cannot write settings.ini: {error}")


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

def resolve_path(working_dir: Path, value) -> Path:
    """
    "temp" and "/temp" -> <working_dir>/temp
    "C:/something"     -> as is (absolute Windows path)
    """
    value = str(value).strip()

    if not value:
        return working_dir

    path = Path(value)

    if path.drive:
        return path

    return working_dir / value.lstrip("/\\")


def get_dirs(base_dir: Path, settings: dict) -> dict[str, Path]:
    base_dir = Path(base_dir).resolve()

    dirs_cfg = settings.get("DIRS", {})
    arch_cfg = settings.get("ARCHITECTURE", {})

    working = Path(str(dirs_cfg.get("working_dir", "") or ""))
    if not working.is_absolute():
        working = (base_dir / working).resolve()

    temp = resolve_path(working, dirs_cfg.get("temp_dir", "/temp"))

    return {
        "working": working,
        "temp": temp,
        "temp_templates": temp / TEMPLATES_DIR_NAME,
        "active": resolve_path(working, arch_cfg.get("active", "./active")),
        "tests": resolve_path(working, arch_cfg.get("tests", "./tests")),
        "complete": resolve_path(working, arch_cfg.get("complete", "./complete")),
        "configs": base_dir / "db" / "tasks_templates",
    }


def ensure_structure(base_dir: Path, settings: dict) -> list[str]:
    """
    Creates all required folders and an example template if there are no templates yet.
    Returns a list of problems (an empty list = everything is fine).
    """
    problems = []
    dirs = get_dirs(base_dir, settings)

    for path in dirs.values():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            problems.append(f"Cannot create {path}: {error}")

    configs = dirs["configs"]

    try:
        if configs.is_dir() and not any(configs.glob("*.json")):
            with (configs / "empty.json").open("w", encoding="utf-8") as file:
                json.dump(EXAMPLE_TEMPLATE, file, ensure_ascii=False, indent=4)
    except OSError as error:
        problems.append(f"Cannot create example template: {error}")

    return problems