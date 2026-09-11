import sys
import threading
import traceback
import tkinter as tk
from pathlib import Path
# from scripts.main import main
from tkinter import messagebox

    
BASE_DIR = Path('./')

root = tk.Tk()
root.title("Toolkit")

def open_settigns():
    window = tk.Toplevel(root)
    window.title("Settings")
    
    working_path = tk.Label(window, text="Enter the base path ")