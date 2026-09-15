import os
import shutil
from pathlib import Path

def activate_new_task(
    base_dir: Path,
    name_of_task: str,
    tmp_dir: Path
) -> None:

    base_dir = base_dir / name_of_task
    backup_dir = base_dir / "backup"

    if not base_dir.is_dir():
        base_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    backup_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    src_files = os.listdir(tmp_dir)

    for file_name in src_files:

        full_file_name = tmp_dir / file_name

        if not full_file_name.is_file():
            continue

        shutil.copy(
            full_file_name,
            base_dir
        )

        if file_name != "template.ipynb":
            shutil.move(
                full_file_name,
                backup_dir
            )