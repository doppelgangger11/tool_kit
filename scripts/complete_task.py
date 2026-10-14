from __future__ import annotations

import os
import shutil
import stat
import sys
import zipfile

from datetime import datetime
from pathlib import Path
from typing import Callable, NamedTuple


SNAPSHOT_EXCLUDE = (
    ".venv", "venv", "node_modules", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ipynb_checkpoints",
)


class ProjectInfo(NamedTuple):
    name: str
    path: Path
    modified: datetime


class CompleteResult(NamedTuple):
    destination: Path
    backup: Path | None
    warnings: list
    how: str            # renamed | copied | zipped


# ---------------------------------------------------------
# Listing / naming
# ---------------------------------------------------------

def list_projects(active_dir) -> list[ProjectInfo]:
    active_dir = Path(active_dir)

    if not active_dir.is_dir():
        return []

    projects = []

    for item in active_dir.iterdir():
        try:
            if (
                item.is_dir()
                and not item.is_symlink()
                and not item.name.startswith(".")
            ):
                projects.append(ProjectInfo(
                    item.name,
                    item,
                    datetime.fromtimestamp(item.stat().st_mtime),
                ))
        except OSError:
            continue

    return sorted(projects, key=lambda p: p.name.lower())


def target_path(dest_dir, name: str, mode: str) -> Path:
    return Path(dest_dir) / (f"{name}.zip" if mode == "zip" else name)


def free_target(dest_dir, name: str, mode: str) -> Path:
    base = target_path(dest_dir, name, mode)

    if not base.exists():
        return base

    stamp = datetime.now().strftime("%Y%m%d")
    number = 1

    while True:
        suffix = f"_{stamp}" if number == 1 else f"_{stamp}_{number}"
        candidate = target_path(dest_dir, f"{name}{suffix}", mode)
        if not candidate.exists():
            return candidate
        number += 1


# ---------------------------------------------------------
# Zip
# ---------------------------------------------------------

def zip_directory(src, zip_path, exclude=(), log: Callable | None = None) -> int:
    src = Path(src)
    zip_path = Path(zip_path)
    part = zip_path.with_name(zip_path.name + ".part")

    zip_path.parent.mkdir(parents=True, exist_ok=True)

    excluded = {name.lower() for name in exclude}
    count = 0

    try:
        with zipfile.ZipFile(
            part, "w", zipfile.ZIP_DEFLATED, allowZip64=True
        ) as archive:
            for root, dirs, files in os.walk(src):
                dirs[:] = [
                    d for d in dirs
                    if d.lower() not in excluded
                    and not os.path.islink(os.path.join(root, d))
                ]

                rel_root = Path(root).relative_to(src.parent)

                archive.write(root, str(rel_root))

                for filename in files:
                    path = os.path.join(root, filename)
                    if os.path.islink(path):
                        continue

                    archive.write(path, str(rel_root / filename))
                    count += 1

                    if log and count % 200 == 0:
                        log(f"Zipping... {count} files")

        with zipfile.ZipFile(part) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"Archive check failed: {bad}")

        os.replace(part, zip_path)

    except BaseException:
        try:
            part.unlink()
        except OSError:
            pass
        raise

    return count


# ---------------------------------------------------------
# Move / remove
# ---------------------------------------------------------

def _count_files(path) -> int:
    return sum(len(files) for _, _, files in os.walk(path))


def remove_tree(path) -> list[str]:
    errors: list[str] = []

    def fix(func, target, error):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except OSError as exc:
            errors.append(f"{target}: {exc}")

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=lambda f, p, e: fix(f, p, e))
    else:
        shutil.rmtree(path, onerror=lambda f, p, e: fix(f, p, e))

    return errors


def move_directory(src, dst, log: Callable | None = None):
    src, dst = Path(src), Path(dst)

    if dst.exists():
        raise FileExistsError(f"Already exists: {dst}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        os.rename(src, dst)
        return "renamed", []
    except OSError:
        pass

    if log:
        log("Copying project...")

    try:
        shutil.copytree(src, dst, symlinks=True)

        if _count_files(src) != _count_files(dst):
            raise RuntimeError("Copy check failed: file counts differ.")
    except BaseException:
        shutil.rmtree(dst, ignore_errors=True)
        raise

    if log:
        log("Removing the original...")

    warnings = remove_tree(src)

    if warnings:
        warnings.insert(
            0, "The project was copied, but some files could not be removed "
               f"from the old location ({src}):"
        )

    return "copied", warnings


# ---------------------------------------------------------
# Main entry point
# ---------------------------------------------------------

def _inside(child: Path, parent: Path) -> bool:
    child, parent = child.resolve(), parent.resolve()
    return child == parent or parent in child.parents


def complete_task(
    active_dir,
    name: str,
    dest_dir,
    backup_dir=None,
    mode: str = "folder",
    snapshot: bool = False,
    on_conflict: str = "error",
    log: Callable | None = None,
) -> CompleteResult:
    """
    mode      - folder: relocate ther folder; zip: packeging into <name>.zip and delet the folder
    snapshot  - Create zip-copy into bacup_dir, before relocation into complete/
    on_conflict - error | suffix (add date to name)
    Original folder will be deleted ONLY if packeged into .zip.
    """
    log = log or (lambda message: None)

    if mode not in ("folder", "zip"):
        raise ValueError(f"Unknown mode: {mode}")

    if not name or Path(name).name != name or name in (".", ".."):
        raise ValueError("Invalid project name.")

    active_dir, dest_dir = Path(active_dir), Path(dest_dir)
    src = active_dir / name

    if not src.is_dir() or src.is_symlink():
        raise FileNotFoundError(f"Project not found: {src}")

    if _inside(dest_dir, src):
        raise ValueError("The destination cannot be inside the project.")

    dest_dir.mkdir(parents=True, exist_ok=True)

    target = target_path(dest_dir, name, mode)

    if target.exists():
        if on_conflict == "suffix":
            target = free_target(dest_dir, name, mode)
        else:
            raise FileExistsError(f"Already exists: {target}")

    backup_path = None

    if snapshot:
        if backup_dir is None:
            raise ValueError("Backup folder is not set.")

        backup_path = (
            Path(backup_dir)
            / f"{name}_{datetime.now():%Y%m%d_%H%M%S}.zip"
        )
        log("Creating backup snapshot...")
        zip_directory(src, backup_path, SNAPSHOT_EXCLUDE, log)

    warnings: list[str] = []

    if mode == "zip":
        log("Creating archive...")
        zip_directory(src, target, (), log)

        log("Removing the original...")
        warnings = remove_tree(src)

        if warnings:
            warnings.insert(
                0, "The archive was created, but some files could not be "
                   f"removed from {src}:"
            )

        how = "zipped"

    else:
        log("Moving project...")
        how, warnings = move_directory(src, target, log)

    return CompleteResult(target, backup_path, warnings, how)
