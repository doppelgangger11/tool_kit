from pathlib import Path
import subprocess
import sys

from scripts.settings_manager import read_settings


BASE_DIR = Path(__file__).resolve().parent
REQUIREMENTS_FILE = BASE_DIR / "requirements.txt"


def initialize_directories() -> None:
    directories = [
        BASE_DIR / "db",
        BASE_DIR / "config",
    ]

    for directory in directories:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


def install_requirements() -> None:
    if not REQUIREMENTS_FILE.is_file():
        raise FileNotFoundError(
            f"Requirements file not found: {REQUIREMENTS_FILE}"
        )

    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(REQUIREMENTS_FILE),
        ]
    )


def initialize_database() -> None:
    files = {
        BASE_DIR / "db" / "notes.json": "[]\n",
        BASE_DIR / "db" / "quick_commands.ini": "",
    }

    for path, default_content in files.items():
        if not path.exists():
            path.write_text(
                default_content,
                encoding="utf-8",
            )


def initialize_settings() -> None:
    read_settings(BASE_DIR / "db")


def initialize() -> None:
    print("=" * 40)
    print("Initializing Toolkit...")
    print("=" * 40)

    print("\n[1/4] Initializing directories...")
    initialize_directories()

    print("\n[2/4] Installing requirements...")
    install_requirements()

    print("\n[3/4] Initializing database...")
    initialize_database()

    print("\n[4/4] Initializing settings...")
    initialize_settings()

    print("\nToolkit initialization complete.")
    print("=" * 40)


if __name__ == "__main__":
    initialize()