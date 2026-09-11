import os
import shutil

tmp_dir = "./temp"

name_of_task = input('>>> ')

base_dir = f'./active/{name_of_task}/'
backup_dir = f'./active/{name_of_task}/backup/'

if not os.path.isdir(base_dir):
    os.mkdir(base_dir)
    os.mkdir(backup_dir)


src_files = os.listdir(tmp_dir)
for file_name in src_files:
    full_file_name = os.path.join(tmp_dir, file_name)
    # print(repr(full_file_name))
    if os.path.isfile(full_file_name):
        shutil.copy(full_file_name, base_dir)
        if full_file_name != './temp\\template.ipynb':
            shutil.move(full_file_name, backup_dir)
              