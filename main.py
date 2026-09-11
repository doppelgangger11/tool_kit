from pathlib import Path

from scripts.init import initialize_project
from scripts.activation_new_task import activate_new_task


start_script: dict[str, bool] = {
    'init': True,
    'activate_proj': False,
}

BASE_DIR = Path('./')

SCRIPTS_DIR = BASE_DIR / 'scripts'
LOG_DIR = BASE_DIR / 'logs'

#  -----------------------------------------
# | Проверка целостности структуры проекта |
# -----------------------------------------
if start_script['init']:
    list_dirs = [
        LOG_DIR,
    ]

    for dir in list_dirs:
        if not dir.is_dir():
            initialize_project(list_dirs=list_dirs)
# ---------------------------------------------        

#  -----------------------------------
# | Система активации нового проекта |
# -----------------------------------
if start_script['activate_proj']:
    PROJECTS_DIR = Path('../')

    activate_new_task(base_dir=PROJECTS_DIR / 'active', name_of_task=str(), tmp_dir=PROJECTS_DIR / 'temp')
# ---------------------------------------------