#!/usr/bin/env python3
"""
Toolkit: setup and launcher.

    python init.py                  check the system, install what is missing,
                                    create settings and folders, start Toolkit
    python init.py --no-launch      everything except starting Toolkit
    python init.py --no-install     only report what is missing
    python init.py --no-scan        install only the packages from REQUIRED_PACKAGES
    python init.py --workdir PATH   folder for projects (saved to settings.ini)
    python init.py --ask            ask for that folder interactively

Safe to run again at any time: it only fixes what is missing, so it can also
be used as the everyday launcher.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import importlib.util
import os
import shutil
import subprocess
import sys
import time
import traceback

from datetime import datetime
from pathlib import Path


MIN_PYTHON = (3, 10)

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "settings.ini"
LOG_FILE = BASE_DIR / "logs" / "toolkit.log"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# ============================================================
# WHAT THE PROJECT NEEDS
# ============================================================

# import name -> package name on PyPI.
# Packages that must be present even if the scan below does not find them.
REQUIRED_PACKAGES = {
    "pystray": "pystray",
    "PIL": "pillow",
    "tqdm": "tqdm",
}

# Only the Toolkit's own source is scanned for imports. Your projects
# (the working folder) are never scanned, so their dependencies
# (airflow and so on) are never installed here.
SOURCE_DIRS = ("scripts", "interface", "games")

SKIP_DIRS = {
    "__pycache__", "node_modules", "site-packages", "venv", "env",
    "build", "dist",
}

# When the import name differs from the PyPI name
PIP_ALIASES = {
    "PIL": "pillow", "cv2": "opencv-python", "yaml": "pyyaml",
    "sklearn": "scikit-learn", "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil", "dotenv": "python-dotenv",
    "docx": "python-docx", "serial": "pyserial", "jwt": "pyjwt",
    "git": "gitpython", "attr": "attrs", "usb": "pyusb",
    "Crypto": "pycryptodome", "OpenSSL": "pyopenssl",
    "win32api": "pywin32", "win32con": "pywin32", "win32gui": "pywin32",
    "win32com": "pywin32", "pythoncom": "pywin32", "pywintypes": "pywin32",
}

# Optional external programs: only reported, never installed
OPTIONAL_TOOLS = {
    "docker": "Docker Manager needs Docker Desktop "
              "(https://www.docker.com/products/docker-desktop/)",
}

# Used only if NotesManager cannot start without a notes file
DEFAULT_NOTES_JSON = "[]"

STARTUP_WAIT = 4.0          # seconds to watch that Toolkit did not crash


# ============================================================
# OUTPUT
# ============================================================

def _make_console_safe() -> None:
    # legacy Windows consoles (cp866/cp1251) must never crash on a symbol
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass


def say(text: str = "") -> None:
    print(text, flush=True)


def step(number: int, total: int, title: str) -> None:
    say()
    say(f"[{number}/{total}] {title}")


def good(text: str) -> None:
    say(f"   OK    {text}")


def note(text: str) -> None:
    say(f"         {text}")


def warn(text: str) -> None:
    say(f"   !!    {text}")


def bad(text: str) -> None:
    say(f"   FAIL  {text}")


class Report:
    """What happened during this run."""

    def __init__(self) -> None:
        self.changes: list[str] = []
        self.warnings: list[str] = []
        self.blockers: list[str] = []


# ============================================================
# 1. SYSTEM
# ============================================================

def is_importable(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def run_pip(args: list[str], timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pip", *args,
         "--disable-pip-version-check", "--no-input", "--progress-bar", "off"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
    )


def ensure_pip() -> bool:
    if is_importable("pip"):
        return True

    try:
        result = subprocess.run(
            [sys.executable, "-m", "ensurepip", "--upgrade"],
            capture_output=True, text=True, errors="replace", timeout=300,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    importlib.invalidate_caches()
    return result.returncode == 0 and is_importable("pip")


def tkinter_hint() -> str:
    if os.name == "nt":
        return ("Run the Python installer again, choose Modify and tick "
                "'tcl/tk and IDLE'.")
    if sys.platform == "darwin":
        return "Install it with: brew install python-tk"
    return "Install it with: sudo apt install python3-tk"


def find_pythonw() -> Path | None:
    if os.name != "nt":
        return None

    candidate = Path(sys.executable).with_name("pythonw.exe")
    if candidate.is_file():
        return candidate

    found = shutil.which("pythonw")
    return Path(found) if found else None


def check_system(report: Report) -> None:
    good(f"Python {sys.version.split()[0]}  ({sys.executable})")

    if not (is_importable("tkinter") and is_importable("_tkinter")):
        report.blockers.append(
            f"tkinter is missing, Toolkit cannot show windows. {tkinter_hint()}"
        )
        bad("tkinter is missing")
    else:
        good("tkinter")

    if ensure_pip():
        good("pip")
    else:
        report.blockers.append(
            "pip is missing and could not be installed automatically. "
            "Reinstall Python from python.org with pip enabled."
        )
        bad("pip is missing")

    if os.name == "nt":
        pythonw = find_pythonw()
        if pythonw:
            good(f"pythonw  ({pythonw})")
        else:
            warn("pythonw.exe not found; Toolkit will start without a "
                 "console through python.exe instead")
    else:
        note(f"platform: {sys.platform} (some features, for example global "
             "hotkeys and the tray, are designed for Windows)")


# ============================================================
# 2. DEPENDENCIES
# ============================================================

class _ImportCollector(ast.NodeVisitor):
    """
    Collects top-level import names, skipping optional imports:
    inside try/except ImportError and inside `if TYPE_CHECKING`.
    """

    def __init__(self) -> None:
        self.names: set[str] = set()
        self._optional = 0

    def visit_Import(self, node: ast.Import) -> None:
        if not self._optional:
            self.names.update(alias.name.split(".")[0] for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if not self._optional and node.level == 0 and node.module:
            self.names.add(node.module.split(".")[0])

    @staticmethod
    def _catches_import_error(handler: ast.ExceptHandler) -> bool:
        wanted = {"ImportError", "ModuleNotFoundError", "Exception"}

        if handler.type is None:
            return True
        if isinstance(handler.type, ast.Name):
            return handler.type.id in wanted
        if isinstance(handler.type, ast.Tuple):
            return any(
                isinstance(item, ast.Name) and item.id in wanted
                for item in handler.type.elts
            )
        return False

    def visit_Try(self, node) -> None:
        if any(self._catches_import_error(h) for h in node.handlers):
            self._optional += 1
            for child in node.body:
                self.visit(child)
            self._optional -= 1

            for child in [*node.handlers, *node.orelse, *node.finalbody]:
                self.visit(child)
        else:
            self.generic_visit(node)

    if hasattr(ast, "TryStar"):
        visit_TryStar = visit_Try

    def visit_If(self, node: ast.If) -> None:
        test = node.test
        is_type_checking = (
            (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING")
            or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")
        )

        if is_type_checking:
            for child in node.orelse:
                self.visit(child)
        else:
            self.generic_visit(node)


def _source_files(base_dir: Path) -> list[Path]:
    files = sorted(base_dir.glob("*.py"))

    for name in SOURCE_DIRS:
        folder = base_dir / name
        if not folder.is_dir():
            continue

        for path in sorted(folder.rglob("*.py")):
            parts = path.relative_to(base_dir).parts[:-1]
            if any(p in SKIP_DIRS or p.startswith(".") for p in parts):
                continue
            files.append(path)

    return files


def scan_imports(base_dir: Path = BASE_DIR) -> dict[str, list[str]]:
    stdlib = set(sys.stdlib_module_names) | {"__future__"}

    top_level_local = {p.stem for p in base_dir.glob("*.py")}
    top_level_local |= {p.name for p in base_dir.iterdir() if p.is_dir()}

    found: dict[str, list[str]] = {}

    for path in _source_files(base_dir):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue

        collector = _ImportCollector()
        collector.visit(tree)

        siblings = {p.stem for p in path.parent.glob("*.py")}
        siblings |= {p.name for p in path.parent.iterdir() if p.is_dir()}

        for name in collector.names:
            if name in stdlib or name in top_level_local or name in siblings:
                continue
            if os.name != "nt" and name.startswith("win32"):
                continue

            found.setdefault(name, []).append(
                path.relative_to(base_dir).as_posix()
            )

    return found


def find_missing(scan: bool = True) -> list[tuple[str, str, str]]:
    missing: list[tuple[str, str, str]] = []
    seen_packages: set[str] = set()

    for import_name, package in REQUIRED_PACKAGES.items():
        if not is_importable(import_name) and package not in seen_packages:
            missing.append((import_name, package, "required"))
            seen_packages.add(package)

    if scan:
        for import_name, files in sorted(scan_imports().items()):
            package = PIP_ALIASES.get(import_name, import_name)

            if is_importable(import_name) or package in seen_packages:
                continue

            extra = f" (+{len(files) - 1})" if len(files) > 1 else ""
            missing.append((import_name, package, f"used in {files[0]}{extra}"))
            seen_packages.add(package)

    return missing


def _permission_problem(text: str) -> bool:
    text = text.lower()
    return any(k in text for k in (
        "permission denied", "access is denied", "errno 13",
        "winerror 5", "not writeable", "not writable",
    ))


def _short_error(result: subprocess.CompletedProcess) -> str:
    lines = [
        line.strip()
        for line in (result.stderr + "\n" + result.stdout).splitlines()
        if line.strip()
    ]
    errors = [line for line in lines if line.upper().startswith("ERROR")]
    pick = (errors or lines or ["unknown pip error"])[-1]
    return pick[:200]


def _network_hint(text: str) -> str:
    text = text.lower()
    keys = ("no matching distribution", "could not find a version",
            "connection", "proxy", "ssl", "timed out", "temporary failure",
            "name or service not known")

    if any(k in text for k in keys):
        return ("Check the internet connection (behind a proxy set HTTPS_PROXY), "
                "or that the package name is correct.")
    return ""


def pip_install(packages: list[str]) -> subprocess.CompletedProcess:
    result = run_pip(["install", *packages])

    if result.returncode != 0 and _permission_problem(result.stderr + result.stdout):
        result = run_pip(["install", "--user", *packages])

    return result


def install_packages(missing, verify=is_importable):
    if not missing:
        return [], []

    installed, failed = [], []
    packages = sorted({package for _, package, _ in missing})

    try:
        result = pip_install(packages)
    except (OSError, subprocess.SubprocessError) as error:
        return [], [(i, p, str(error)) for i, p, _ in missing]

    outcome: dict[str, str] = {}

    if result.returncode != 0:
        for package in packages:
            try:
                single = pip_install([package])
            except (OSError, subprocess.SubprocessError) as error:
                outcome[package] = str(error)
                continue

            if single.returncode != 0:
                text = _short_error(single)
                hint = _network_hint(single.stderr + single.stdout)
                outcome[package] = f"{text} {hint}".strip()

    importlib.invalidate_caches()

    for import_name, package, _ in missing:
        if package in outcome:
            failed.append((import_name, package, outcome[package]))
        elif verify(import_name):
            installed.append((import_name, package, ""))
        else:
            failed.append((
                import_name, package,
                "installed, but cannot be imported (restart init.py)",
            ))

    return installed, failed


def check_dependencies(report: Report, install: bool, scan: bool) -> None:
    missing = find_missing(scan=scan)

    if not missing:
        good("all packages are installed")
        return

    for import_name, package, why in missing:
        note(f"missing: {package}  ({why})")

    if not install:
        for _, package, why in missing:
            report.warnings.append(f"package not installed: {package}")
        warn("--no-install: nothing was installed")
        return

    say("         installing, this can take a minute...")
    installed, failed = install_packages(missing)

    for _, package, _ in installed:
        good(f"installed {package}")
        report.changes.append(f"installed {package}")

    for import_name, package, message in failed:
        bad(f"{package}: {message}")

        if import_name in REQUIRED_PACKAGES:
            report.blockers.append(f"required package '{package}' is not installed")
        else:
            report.warnings.append(f"package '{package}' is not installed")


# ============================================================
# 3. SETTINGS AND FOLDERS
# ============================================================

def setup_settings(report: Report, workdir: Path | None, ask: bool) -> dict | None:
    from scripts.settings_manager import (
        ensure_structure, get_dirs, read_settings, write_settings,
    )

    existed = SETTINGS_FILE.is_file()
    settings = read_settings(BASE_DIR)

    chosen = workdir

    if ask and chosen is None and not existed:
        default = get_dirs(BASE_DIR, settings)["working"]
        try:
            answer = input(f"         Working folder for projects [{default}]: ").strip()
        except EOFError:
            answer = ""
        if answer:
            chosen = Path(answer).expanduser().resolve()

    if chosen is not None:
        settings.setdefault("DIRS", {})["working_dir"] = str(chosen)
        try:
            write_settings(BASE_DIR, settings)
        except OSError as error:
            bad(f"cannot write settings.ini: {error}")
            report.blockers.append("settings.ini cannot be written")
            return None

    if SETTINGS_FILE.is_file():
        if existed and chosen is None:
            good("settings.ini")
        else:
            good("settings.ini created")
            report.changes.append("created settings.ini")
    else:
        report.blockers.append(
            "settings.ini could not be created: is the Toolkit folder read-only? "
            "Move it to a folder you can write to."
        )
        bad("settings.ini could not be created")
        return None

    dirs = get_dirs(BASE_DIR, settings)
    problems = ensure_structure(BASE_DIR, settings)

    note(f"working folder: {dirs['working']}")
    note(f"projects folder: {dirs['active']}")

    for problem in problems:
        warn(problem)
        report.warnings.append(problem)

    return settings


# ============================================================
# 4. NOTES
# ============================================================

def ensure_notes(report: Report) -> None:
    path = BASE_DIR / "db" / "notes.json"

    if path.exists():
        good("notes.json")
        return

    try:
        from scripts.note_manager import NotesManager
    except Exception as error:
        note(f"notes: skipped (NotesManager cannot be imported: {error})")
        return

    def can_start() -> bool:
        try:
            NotesManager(path=path).read_notes()
            return True
        except Exception:
            return False

    if can_start():
        good("notes (the file is created on first use)")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_NOTES_JSON, encoding="utf-8")

    if can_start():
        good(f"created empty {path.name}")
        report.changes.append("created db/notes.json")
        return

    path.unlink(missing_ok=True)
    warn("NotesManager cannot read an empty notes file; "
         "set DEFAULT_NOTES_JSON in init.py to its empty format")
    report.warnings.append("notes.json was not created")


# ============================================================
# 5. OPTIONAL TOOLS
# ============================================================

def check_optional_tools() -> None:
    for command, description in OPTIONAL_TOOLS.items():
        if shutil.which(command):
            good(f"{command}")
        else:
            note(f"optional: {command} not found. {description}")


# ============================================================
# 6. LAUNCH
# ============================================================

def _tail(path: Path, offset: int, lines: int = 25) -> str:
    try:
        with open(path, "rb") as file:
            file.seek(offset)
            text = file.read().decode("utf-8", errors="replace")
    except OSError:
        return ""

    return "\n".join(text.strip().splitlines()[-lines:])


def launch_main(wait: float = STARTUP_WAIT) -> tuple[bool, str]:
    main = BASE_DIR / "main.py"
    if not main.is_file():
        return False, "main.py was not found next to init.py"

    executable = find_pythonw() or Path(sys.executable)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    offset = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0

    kwargs: dict = {}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200   # DETACHED | NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")

    with open(LOG_FILE, "ab") as log:
        log.write(
            f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S}  "
            f"{executable.name} {main.name} ===\n".encode("utf-8")
        )
        log.flush()
        offset = log.tell()

        try:
            process = subprocess.Popen(
                [str(executable), str(main)],
                cwd=str(BASE_DIR),
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
                close_fds=True,
                **kwargs,
            )
        except OSError as error:
            return False, f"could not start {executable}: {error}"

    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        code = process.poll()

        if code is not None:
            if code == 0:
                return True, ("Toolkit was already running; it was asked to "
                              "show its window.")

            details = _tail(LOG_FILE, offset)
            return False, (f"Toolkit exited right after start (code {code}).\n"
                           f"{details}\n\nFull log: {LOG_FILE}")

        time.sleep(0.2)

    return True, f"Toolkit is running in the tray. Log: {LOG_FILE}"


# ============================================================
# MAIN
# ============================================================

def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Toolkit: setup and launcher",
        epilog="Safe to run again at any time.",
    )
    parser.add_argument("--no-launch", action="store_true",
                        help="do not start Toolkit at the end")
    parser.add_argument("--no-install", action="store_true",
                        help="only report missing packages, install nothing")
    parser.add_argument("--no-scan", action="store_true",
                        help="install only REQUIRED_PACKAGES, skip the import scan")
    parser.add_argument("--workdir", type=Path, metavar="PATH",
                        help="working folder for projects")
    parser.add_argument("--ask", action="store_true",
                        help="ask for the working folder on first run")
    return parser.parse_args(argv)


def pause_if_interactive() -> None:
    try:
        if sys.stdin and sys.stdin.isatty():
            input("\nPress Enter to close...")
    except (EOFError, OSError):
        pass


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = Report()

    say("=" * 56)
    say("  Toolkit setup")
    say("=" * 56)

    total = 6

    step(1, total, "System")
    check_system(report)

    step(2, total, "Packages")
    if "pip" not in " ".join(report.blockers):
        check_dependencies(report, install=not args.no_install, scan=not args.no_scan)
    else:
        warn("skipped: pip is not available")

    step(3, total, "Settings and folders")
    workdir = args.workdir.expanduser().resolve() if args.workdir else None

    try:
        settings = setup_settings(report, workdir, args.ask)
    except ImportError as error:
        bad(f"cannot import scripts.settings_manager: {error}")
        report.blockers.append("scripts/settings_manager.py is missing")
        settings = None

    step(4, total, "Notes")
    if settings is not None:
        ensure_notes(report)
    else:
        warn("skipped")

    step(5, total, "Optional tools")
    check_optional_tools()

    step(6, total, "Launch")

    say()
    say("-" * 56)

    if report.changes:
        say("Done:")
        for item in report.changes:
            say(f"  + {item}")
    else:
        say("Nothing to fix: everything was already in place.")

    for item in report.warnings:
        warn(item)

    if report.blockers:
        say()
        say("Toolkit was NOT started. Fix this first:")
        for item in report.blockers:
            say(f"  * {item}")
        say("Then run init.py again.")
        return 1

    if args.no_launch:
        say("Setup finished (--no-launch).")
        return 0

    exe = find_pythonw()
    say(f"Starting: {(exe.name if exe else Path(sys.executable).name)} main.py")

    started, message = launch_main()
    say(message)

    if not started:
        return 1

    return 0


if __name__ == "__main__":
    _make_console_safe()

    if sys.version_info < MIN_PYTHON:
        print(
            f"Toolkit needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer, "
            f"this is {sys.version.split()[0]}.\n"
            "Install the latest Python from https://www.python.org/downloads/ "
            "(tick 'Add python.exe to PATH') and run init.py again."
        )
        pause_if_interactive()
        sys.exit(1)

    try:
        exit_code = main()
    except KeyboardInterrupt:
        exit_code = 130
    except Exception:
        say()
        say("Unexpected error in init.py:")
        traceback.print_exc()
        exit_code = 1

    if exit_code != 0:
        pause_if_interactive()
    else:
        time.sleep(1.5)

    sys.exit(exit_code)