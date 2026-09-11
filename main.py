from pathlib import Path

from scripts.init import initialize_project


BASE_DIR = Path('./')

SCRIPTS_DIR = BASE_DIR / 'scripts'
LOG_DIR = BASE_DIR / 'logs'

#  -----------------------------------------
# | Проверка целостности структуры проекта |
# -----------------------------------------
list_dirs = [
    LOG_DIR,
]

for dir in list_dirs:
    if not dir.is_dir():
        initialize_project(list_dirs=list_dirs)
        
