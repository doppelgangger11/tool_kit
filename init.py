from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys


# ============================================================
# PROJECT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "settings.ini"


# ============================================================
# DEFAULTS
# ============================================================

DEFAULT_SETTINGS = {
    "BASE": {
        "log": "False",
    },

    "DIRS": {
        "working_dir": "",
        "temp_dir": "../temp",
        "notes_dir": "./db",
    },

    "PROGRAMS": {},

    "ARCHITECTURE": {},
}


DEFAULT_NOTES = ''


# ============================================================
# DEPENDENCIES
# ============================================================

# import_name: package_name

REQUIRED_PACKAGES = {
    "tqdm": "tqdm",
    "configparser": "configparser",
    "pystray": "pystray",
    "pillow": "pillow",
}


# ============================================================
# SETTINGS
# ============================================================

def create_default_settings(
    working_dir: Path,
) -> dict:
    """
    Creates the initial project configuration.

    working_dir is stored as an absolute path,
    the other directories stay relative.
    """

    settings = {
        section: values.copy()
        for section, values in DEFAULT_SETTINGS.items()
    }

    settings["DIRS"]["working_dir"] = str(
        working_dir
    )

    return settings


def create_settings(
    working_dir: Path,
) -> dict:
    """
    Creates settings.ini.

    Returns:
        The created settings.
    """

    from scripts.settings_manager import write_settings

    settings = create_default_settings(
        working_dir
    )

    write_settings(BASE_DIR, settings)

    return settings


# ============================================================
# WORKING DIRECTORY
# ============================================================

def ask_working_directory() -> Path:
    """
    Asks the user for the directory
    where the application will store its data.

    If the user enters nothing,
    ./data relative to the project is used.
    """

    default_path = BASE_DIR / "data"

    print()
    print("=== First initialization ===")
    print()
    print(
        "Choose a working directory for application data."
    )
    print()
    print(f"Default: {default_path}")
    print()

    path = BASE_DIR
    print(f"Working directory: {BASE_DIR}")
    return path
        
# ============================================================
# DIRECTORY CREATION
# ============================================================

def create_directory(
    path: Path,
) -> bool:
    """
    Creates a directory.

    Returns:
        True  — the directory was created
        False — it already existed
    """

    if path.exists():

        if not path.is_dir():
            raise NotADirectoryError(
                f"Path exists but is not a directory: {path}"
            )

        return False

    path.mkdir(
        parents=True,
        exist_ok=True,
    )

    return True


def create_required_directories(
    settings: dict,
) -> list[Path]:
    """
    Creates only the required directories.

    Currently required:

        working_dir/
        working_dir/temp/
        working_dir/notes/
    """

    working_dir = Path(
        settings["DIRS"]["working_dir"]
    )

    temp_dir = (
        '../' / working_dir
        / settings["DIRS"]["temp_dir"]
    )

    notes_dir = (
        working_dir
        / settings["DIRS"]["notes_dir"]
    )

    directories = [
        working_dir,
        temp_dir,
        notes_dir,
    ]

    created = []

    for directory in directories:

        if create_directory(directory):
            created.append(directory)

    return created


# ============================================================
# NOTES
# ============================================================

def create_notes(
    settings: dict,
) -> Path:
    """
    Creates the initial notes.json.

    If the file already exists, does nothing.
    """

    working_dir = Path(
        settings["DIRS"]["working_dir"]
    )

    notes_dir = (
        working_dir
        / settings["DIRS"]["notes_dir"]
    )

    notes_file = (
        notes_dir / "notes.json"
    )

    if notes_file.exists():
        return notes_file

    notes_file.write_text(
        json.dumps(
            DEFAULT_NOTES,
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    return notes_file


# ============================================================
# DEPENDENCIES
# ============================================================

def check_dependencies() -> list[str]:
    """
    Checks that the required Python packages are present.

    Installs nothing automatically.

    Returns:
        List of missing packages.
    """

    missing = []

    for import_name, package_name in (
        REQUIRED_PACKAGES.items()
    ):

        if importlib.util.find_spec(
            import_name
        ) is None:

            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

            missing.append(
                package_name
            )

    return missing


# ============================================================
# INITIALIZATION
# ============================================================

def initialize_project() -> dict:
    """
    Performs the initial project initialization.

    IMPORTANT:

    This function is NOT self-healing.

    It is intended for the first run.
    """

    result = {
        "success": False,
        "initialized": False,
        "working_dir": None,
        "created": [],
        "missing_packages": [],
    }

    # --------------------------------------------------------
    # Already initialized
    # --------------------------------------------------------

    if SETTINGS_FILE.exists():

        result["initialized"] = True

        from scripts.settings_manager import read_settings

        settings = read_settings(BASE_DIR)

        result["working_dir"] = (
            settings
            .get("DIRS", {})
            .get("working_dir")
        )

        result["missing_packages"] = (
            check_dependencies()
        )

        result["success"] = True

        return result

    # --------------------------------------------------------
    # Choose working directory
    # --------------------------------------------------------

    working_dir = ask_working_directory()

    # --------------------------------------------------------
    # Create settings
    # --------------------------------------------------------

    settings = create_settings(
        working_dir
    )

    result["created"].append(
        SETTINGS_FILE
    )

    # --------------------------------------------------------
    # Create required directories
    # --------------------------------------------------------

    created_directories = (
        create_required_directories(
            settings
        )
    )

    result["created"].extend(
        created_directories
    )

    # --------------------------------------------------------
    # Create notes
    # --------------------------------------------------------

    notes_file = create_notes(
        settings
    )

    result["created"].append(
        notes_file
    )

    # --------------------------------------------------------
    # Dependencies
    # --------------------------------------------------------

    result["missing_packages"] = (
        check_dependencies()
    )

    result["working_dir"] = str(
        working_dir
    )

    result["success"] = True
    result["initialized"] = True

    return result


# ============================================================
# OUTPUT
# ============================================================

def print_init_result(
    result: dict,
) -> None:
    """
    Shows the initialization result.
    """

    print()
    print("=== Initialization ===")
    print()

    if result["initialized"]:
        print("Project initialized.")

    if result["working_dir"]:
        print(
            f"Working directory:\n"
            f"  {result['working_dir']}"
        )

    if result["created"]:

        print()
        print("Created:")

        for path in result["created"]:
            print(f"  + {path}")

    if result["missing_packages"]:

        print()
        print("Missing packages:")

        for package in result["missing_packages"]:
            print(f"  ! {package}")

        print()
        print(
            "Install the missing packages before "
            "using the application."
        )

    print()

    if result["success"]:
        print("Initialization complete.")
    else:
        print("Initialization failed.")

    print()


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    result = initialize_project()

    print_init_result(result)