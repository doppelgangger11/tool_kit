import tkinter as tk
from tkinter import messagebox

from scripts.activation_new_task import activate_new_task

def open_activation(root, WORKING_DIR, BASE_SETTINGS):
    def on_click():
        activate_new_task(
            base_dir=WORKING_DIR / 'active', 
            name_of_task=new_task_inp.get(),
            tmp_dir=WORKING_DIR / 'temp'
        )
        
        messagebox.showinfo('DONE', 'Successfull')
        window.destroy()
        
    window = tk.Toplevel(root)
    window.title("Settings")
    
    # WORKING_DIR = WORKING_DIR / 'active'
    
    new_task_lable = tk.Label(window, text="Enter the Name of the task")
    new_task_lable.pack(pady=10)

    new_task_inp = tk.Entry(window, width=30)
    new_task_inp.pack(pady=5)
    
    new_task_current = tk.Label(
        window, 
        text=f'Current working dir: {WORKING_DIR / 'active'}'
    )
    new_task_current.pack(pady=10)
    
    tk.Button(
        window, 
        text='Start', 
        command=on_click
    ).pack(pady=10)