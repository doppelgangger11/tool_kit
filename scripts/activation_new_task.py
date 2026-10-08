import json
import shutil

from dataclasses import dataclass
from pathlib import Path


TEMPLATES_DIR_NAME = "templates"
INVALID_NAME_CHARS = '<>:"/\\|?*'


class TempCleanupError(Exception):
    """Project created and files copied, but temp could not be cleaned up."""


@dataclass
class ActivationResult:
    project_dir: Path
    temp_copied: bool


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def validate_project_name(name: str) -> str | None:
    """Returns an error message or None if the name is valid."""
    name = name.strip()

    if not name:
        return "Enter project name."

    if name in (".", "..") or name.endswith((".", " ")):
        return "Invalid project name."

    bad = sorted({c for c in name if c in INVALID_NAME_CHARS})
    if bad:
        return f"Name contains invalid characters: {' '.join(bad)}"

    return None


def _is_templates_dir(item: Path) -> bool:
    return item.name.lower() == TEMPLATES_DIR_NAME


def list_temp_items(temp_dir: Path) -> list[Path]:
    """Returns all contents of temp EXCEPT temp/templates."""
    if not temp_dir.is_dir():
        return []

    return sorted(
        item for item in temp_dir.iterdir()
        if not _is_templates_dir(item)
    )


def _replace_variables(value: str, active_folder: Path, project_name: str) -> Path:
    value = value.replace("$active_folder$", str(active_folder))
    value = value.replace("$name_of_project$", project_name)
    return Path(value)


def _load_template(templates_dir: Path, template_name: str) -> dict:
    template_path = templates_dir / template_name

    if not template_path.is_file():
        raise FileNotFoundError(f"Template not found: {template_path}")

    with template_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _final_name(source: Path, file_config: dict) -> str:
    new_name = str(file_config.get("new_name", "")).strip()

    if not file_config.get("is_rename", False) or not new_name:
        return source.name

    # dag + dag.py -> dag.py
    if not new_name.lower().endswith(source.suffix.lower()):
        new_name += source.suffix

    return new_name


def _check_template(template: dict, templates_dir: Path) -> None:
    """Check everything BEFORE creating anything on disk."""
    for file_config in template.get("files", []):
        name = file_config.get("template", "")

        if name and not (templates_dir / name).is_file():
            raise FileNotFoundError(
                f"Template file not found: {templates_dir / name}"
            )


# ---------------------------------------------------------
# Steps
# ---------------------------------------------------------

def _create_directories(template: dict, active_folder: Path, project_name: str) -> None:
    for directory in template.get("dirs", []):
        _replace_variables(directory, active_folder, project_name).mkdir(
            parents=True, exist_ok=True
        )


def _copy_from_temp(
    template: dict,
    temp_dir: Path,
    active_folder: Path,
    project_name: str,
) -> bool:
    """
    Copies everything from temp (except temp/templates) into
    the template directories.

    True  -> files were copied and verified, temp can be cleaned.
    False -> nothing to copy or no destination, temp is left untouched.
    """
    config = template.get("copy_from_temp", {})

    if not config.get("is_copy", False):
        return False

    directories = config.get("dirs", [])
    sources = list_temp_items(temp_dir)

    if not directories or not sources:
        return False

    for directory in directories:
        destination = _replace_variables(directory, active_folder, project_name)
        destination.mkdir(parents=True, exist_ok=True)

        for source in sources:
            target = destination / source.name

            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                shutil.copy2(source, target)

            # Verify: temp can only be cleaned if the copy exists.
            if not target.exists():
                raise RuntimeError(f"Copy failed: {source} -> {target}")

    return True


def _copy_template_files(
    template: dict,
    templates_dir: Path,
    active_folder: Path,
    project_name: str,
) -> None:
    """Files from temp/templates are only read (copy-paste), never deleted."""
    for file_config in template.get("files", []):
        template_file = file_config.get("template", "")

        if not template_file:
            continue

        source = templates_dir / template_file
        new_name = _final_name(source, file_config)

        for directory in file_config.get("dirs", []):
            destination_dir = _replace_variables(
                directory, active_folder, project_name
            )
            destination_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination_dir / new_name)


def _clear_temp(temp_dir: Path) -> None:
    """Cleans temp; temp/templates is ALWAYS skipped."""
    errors = []

    for item in list_temp_items(temp_dir):
        try:
            if item.is_dir() and not item.is_symlink():
                shutil.rmtree(item)
            else:
                item.unlink()
        except OSError as error:
            errors.append(f"{item.name}: {error}")

    if errors:
        raise TempCleanupError(
            "Project created, but some files in temp could not be removed:\n\n"
            + "\n".join(errors)
        )


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

def activate_new_task(
    base_dir: Path,
    name_of_task: str,
    tmp_dir: Path,
    template_name: str,
    configs_dir: Path,
) -> ActivationResult:

    error = validate_project_name(name_of_task)
    if error:
        raise ValueError(error)

    name_of_task = name_of_task.strip()
    base_dir = Path(base_dir)
    tmp_dir = Path(tmp_dir)
    files_dir = tmp_dir / TEMPLATES_DIR_NAME
    project_dir = base_dir / name_of_task

    if project_dir.exists():
        raise FileExistsError(f"Project already exists: {project_dir}")

    template = _load_template(Path(configs_dir), template_name)
    _check_template(template, files_dir)

    try:
        _create_directories(template, base_dir, name_of_task)
        copied = _copy_from_temp(template, tmp_dir, base_dir, name_of_task)
        _copy_template_files(template, files_dir, base_dir, name_of_task)
    except Exception:
        shutil.rmtree(project_dir, ignore_errors=True)
        raise

    if copied:
        _clear_temp(tmp_dir)

    return ActivationResult(project_dir=project_dir, temp_copied=copied)