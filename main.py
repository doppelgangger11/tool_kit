import argparse
from pathlib import Path

from scripts.init import initialize_project
from scripts.activation_new_task import activate_new_task
from scripts.settings_manager import read_settings, write_settings

from interface.open_settings_util import open_settings

import threading
import traceback
import tkinter as tk
# from scripts.main import main
from tkinter import messagebox

    
BASE_DIR = Path('./')

BASE_SETTINGS = read_settings(directory=BASE_DIR)

root = tk.Tk()
root.title("Toolkit")


settings_button = tk.Button(
    root,
    text='Settings',
    command=lambda: open_settings(
        root=root,
        BASE_DIR=BASE_DIR,
        BASE_SETTINGS=BASE_SETTINGS
    )
)
settings_button.pack(pady=10)

tk.Button(root, text="Exit", command=root.destroy).pack()
root.mainloop()

# #  ------------------------------------
# # | Добавление параметров в терминале |
# # ------------------------------------
# parser = argparse.ArgumentParser(
#     prog="Toolkit",
#     description="Automation routine tasks!",
#     epilog="Created by Markus"
# )

# # interface [bool] CLI/GUI
# parser.add_argument(
#     '-i', '--interface',
#     action='store_true',
#     help="Change CLI to GUI interface"
# )

# # Turn on logging system [bool] add .log
# parser.add_argument(
#     '--log',
#     action='store_true',
#     help="Turn on logfile generation"
# )

# BASE_SETTINGS = parser.parse_args()
# print(f"{BASE_SETTINGS = }")

# #  --------------------
# # | Запуск интерфейса |
# # ---------------------
# if BASE_SETTINGS.interface:
#     print("<<< START GUI INTERFACE >>>")
#     try:
#         from interface import main
#     except ModuleNotFoundError:
#         print("!!! GUI is not defined !!!")
#     except Exception as e:
#         print(f"Error: {e}")
#         print("!!! GUI is collapsed !!!")
#     # exit()
    
# ---------------------------------------------        
    
# print("<<< GUI is inactive >>>")

# start_script: dict[str, bool] = {
#     'init': True,
#     'activate_proj': False,
# }

# BASE_DIR = Path('./')

# SCRIPTS_DIR = BASE_DIR / 'scripts'
# LOG_DIR = BASE_DIR / 'logs'

# #  -----------------------------------------
# # | Проверка целостности структуры проекта |
# # -----------------------------------------
# if start_script['init']:
#     list_dirs = list()
#     if BASE_SETTINGS.log:
#         list_dirs.append(LOG_DIR)

#     for dir in list_dirs:
#         if not dir.is_dir():
#             initialize_project(list_dirs=list_dirs)
#     else:
#         print('<<< File system is ok! >>>')
# # ---------------------------------------------        

# #  -----------------------------------
# # | Система активации нового проекта |
# # -----------------------------------
# if start_script['activate_proj']:
#     PROJECTS_DIR = Path('../')

#     activate_new_task(base_dir=PROJECTS_DIR / 'active', name_of_task=str(), tmp_dir=PROJECTS_DIR / 'temp')
# # ---------------------------------------------