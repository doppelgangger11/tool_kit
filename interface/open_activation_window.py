import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from scripts.activation_new_task import activate_new_task

def open_activation(root, WORKING_DIR, BASE_SETTINGS):
    def on_click():
        activate_new_task(
            base_dir=active_dir, 
            name_of_task=new_task_inp.get(),
            tmp_dir=temp_dir
        )
        
        messagebox.showinfo('DONE', 'Successfull')
        window.destroy()
        
    working_dir = Path(
        BASE_SETTINGS["DIRS"]["working_dir"]
    )

    temp_dir = working_dir / BASE_SETTINGS["DIRS"]["temp_dir"]

    active_dir = working_dir / BASE_SETTINGS["ARCHITECTURE"]["active"]

    window = tk.Toplevel(root)
    window.title("Settings")
    
    # WORKING_DIR = WORKING_DIR / 'active'
    
    new_task_lable = tk.Label(window, text="Enter the Path of the task")
    new_task_lable.pack(pady=10)

    new_task_inp = tk.Entry(window, width=30)
    new_task_inp.pack(pady=5)
    
    new_task_current = tk.Label(
        window, 
        text=f'Current working dir: {WORKING_DIR}'
    )
    new_task_current.pack(pady=10)
    
    tk.Button(
        window, 
        text='Start', 
        command=on_click
    ).pack(pady=10)
    
    window.update_idletasks()

    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()

    window.geometry(f"{width + 20}x{height + 20}")