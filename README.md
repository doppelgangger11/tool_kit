
# Toolkit

Personal Python desktop toolkit for managing projects, tasks, notes, settings, and frequently used development utilities.

Toolkit is a small modular application built with Python and Tkinter. It combines several everyday development utilities in one place instead of relying on a collection of separate scripts.

## Features

### Project Initialization

Toolkit performs a first-run project initialization through `init.py`.

The initialization process:

* creates the initial `settings.ini`;
* configures the application working directory;
* creates required directories;
* creates the initial `notes.json`;
* checks required Python dependencies;
* installs missing Python packages when necessary;
* reports the initialization result.

Initialization is designed for the **first launch** of the application and is not intended to act as a self-healing system.

Once `settings.ini` exists, the project is considered initialized and the existing configuration is loaded instead of recreating the project structure.

### Project & Task Management

* Project initialization
* Task/project activation
* Configurable working directory
* Configurable project directory architecture
* Automatic creation of required directories
* Task activation and workspace management

### Settings

Toolkit uses `settings.ini` for persistent configuration.

The configuration system supports:

* application settings;
* working directory;
* temporary directory;
* notes directory;
* program configuration;
* project architecture;
* optional logging.

Settings can be managed through the graphical interface.

### Quick Notes

Toolkit includes a lightweight local notes manager for storing development notes and temporary information.

Features include:

* Create notes
* Edit notes
* Delete notes
* Automatic timestamps
* Note themes/titles
* Scrollable notes list
* Multiline text editor
* Undo/redo
* Keyboard shortcuts

Supported editor shortcuts:

```text
Ctrl + C    Copy
Ctrl + V    Paste
Ctrl + X    Cut
Ctrl + A    Select all
Ctrl + Z    Undo
Ctrl + Y    Redo
Ctrl + S    Save
```

Notes are stored locally in `notes.json`.

### Quick Commands

Toolkit provides a GUI for frequently used development and system commands.

Examples include:

```text
Git
├── git status
├── git pull
├── git push
└── git diff

Python
├── python --version
├── pip --version
├── pip list
└── pip freeze

Development
├── Open CMD here
├── Open PowerShell here
├── Open VS Code here
└── Open Explorer here
```

Commands are intended to operate relative to the configured working directory.

### Utilities & Games

Toolkit can also contain small standalone utilities and experiments.

Current examples include:

* Minesweeper
* Tic-Tac-Toe

Additional utilities can be added as independent modules without significantly changing the core application.

---

## Project Structure

```text
Toolkit/
│
├── main.py
├── settings.ini
│
├── scripts/
│   ├── init.py
│   ├── activation_new_task.py
│   ├── settings_manager.py
│   └── ...
│
├── interface/
│   ├── open_settings_util.py
│   ├── notes.py
│   └── ...
│
├── games/
│   ├── minesweeper/
│   ├── tic_tac_toe/
│   └── ...
│
├── db/
│   └── notes.json
│
├── logs/
│
└── ...
```

The exact project structure may change as new utilities are added.

---

## Main Components

### `main.py`

Main entry point of the application.

Responsible for:

* starting Toolkit;
* processing command-line arguments;
* initializing the project;
* loading configuration;
* launching the GUI;
* starting required modules.

### `scripts/init.py`

Handles the initial project setup.

Responsibilities include:

* defining default configuration;
* creating `settings.ini`;
* determining the working directory;
* creating required directories;
* creating the initial notes database;
* checking required Python packages;
* installing missing dependencies;
* returning initialization status information.

The initialization process is intentionally  **not self-healing** . Existing configuration is preserved and reused on subsequent launches.

### `scripts/activation_new_task.py`

Handles creation and activation of new tasks/projects according to the configured project architecture.

### `scripts/settings_manager.py`

Responsible for reading and writing Toolkit configuration.

It provides the interface between `settings.ini` and the Python application.

### `interface/`

Contains the Tkinter graphical interface.

Current GUI components include functionality for:

* settings;
* task activation;
* notes;
* quick commands;
* other utilities.

### `games/`

Contains standalone games and experimental modules.

### `db/`

Contains local application data.

For example:

```text
db/
└── notes.json
```

No external database is required.

### `logs/`

Directory used for optional application logging when logging is enabled.

---

## Configuration

Toolkit uses `settings.ini` for persistent configuration.

A minimal configuration may look like:

```ini
[BASE]
log = false

[DIRS]
working_dir = C:/Projects/Toolkit
temp_dir = ../temp
notes_dir = ./db

[PROGRAMS]

[ARCHITECTURE]
```

During first initialization, default settings are generated automatically.

The working directory is stored as an absolute path, while other directory settings can remain relative to it.

The configuration can subsequently be edited through the Toolkit settings interface.

---

## Initialization

On the first launch, Toolkit performs the initialization process.

Conceptually:

```text
First launch
     │
     ▼
Check settings.ini
     │
     ├── exists ──────────────► Load existing settings
     │
     └── does not exist
              │
              ▼
       Create default settings
              │
              ▼
       Create directories
              │
              ▼
        Create notes.json
              │
              ▼
       Check dependencies
              │
              ▼
        Initialization done
```

The initialization function returns a result dictionary containing information such as:

```python
{
    "success": True,
    "initialized": True,
    "working_dir": "...",
    "created": [...],
    "missing_packages": [...]
}
```

---

## Dependencies

Toolkit requires Python 3.x and Tkinter.

Some functionality also uses additional Python packages.

Current dependencies checked during initialization include:

```text
tqdm
configparser
pystray
```

Missing packages are handled by the initialization process using the current Python interpreter:

```bash
python -m pip install <package>
```

The exact dependency list may change as new features are added.

---

## Running

### GUI

Start Toolkit normally:

```bash
python main.py
```

### CLI

Toolkit also supports command-line arguments.

Display available options:

```bash
python main.py --help
```

Example options:

```text
-i, --interface    Launch GUI interface
--log              Enable logging
```

Additional CLI options may be added as the project evolves.

### Initialization Directly

The initialization module can also be executed directly:

```bash
python scripts/init.py
```

This runs the initialization procedure and prints the resulting status.

---

## Requirements

* Python 3.x
* Tkinter
* Git — required only for Git-related commands
* VS Code — optional, for the VS Code launcher
* Additional Python packages used by Toolkit

No external database or web service is required for the core application.

---

## Design Goals

Toolkit is primarily a personal development environment rather than a general-purpose framework.

The project focuses on:

* reducing repetitive development tasks;
* keeping frequently used tools in one place;
* experimenting with Python application architecture;
* practicing Tkinter GUI development;
* creating reusable utilities;
* managing small personal projects and tasks;
* keeping application data local;
* making project configuration accessible through a GUI;
* allowing new features to be added as independent modules.

The application is intentionally lightweight and modular.

---

## Status

**Work in progress.**

Toolkit is an actively evolving personal project. Features, interfaces, configuration options, and project structure may change as new utilities are developed.

Some components are experimental and may be redesigned or replaced.

---

## Author

Created by  **Markus** .
