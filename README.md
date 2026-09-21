
# Toolkit

Personal Python desktop toolkit for managing projects, notes, tasks, settings, and frequently used development utilities.

Toolkit is a small modular application built with Python and Tkinter. It combines several everyday development utilities in one place instead of relying on a collection of separate scripts.

## Features

### Project & Task Management

* Project initialization
* Task/project activation
* Configurable project directory architecture
* Working directory management
* Automatic creation of configured directories
* Task activation and workspace management

### Settings

* Persistent configuration via `settings.ini`
* Configurable working directory
* Configurable project architecture
* Program configuration
* Optional logging
* GUI-based settings management

### Quick Notes

A built-in lightweight notes manager for storing development notes and temporary information.

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

Notes are stored locally and do not require an external database.

### Quick Commands

A GUI for frequently used development and system commands.

Planned/available commands include:

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

Commands are executed relative to the configured working directory.

### Utilities & Games

Toolkit also provides small standalone utilities and experiments that can be launched from the GUI.

Current examples include:

* Minesweeper
* Tic-Tac-Toe
* Additional utilities can be added as independent modules

The project is intentionally modular, so experimental features do not have to be tightly coupled to the main application.

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
│   ├── ...
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

The exact structure may change as new utilities and modules are added.

---

## Main Components

### `main.py`

Main entry point of the application.

Responsible for:

* starting Toolkit;
* processing command-line arguments;
* loading configuration;
* initializing the project environment;
* launching the GUI;
* starting the required modules.

### `scripts/`

Contains the core application logic.

Examples:

* `init.py` — project/environment initialization.
* `activation_new_task.py` — task/project activation.
* `settings_manager.py` — reading and writing configuration.
* Additional modules provide reusable application functionality.

### `interface/`

Contains the Tkinter-based graphical interface.

Examples include:

* settings management;
* notes;
* task activation;
* quick commands;
* other GUI utilities.

### `games/`

Contains standalone games and experiments implemented as independent modules.

### `db/`

Contains local application data.

For example:

```text
db/
└── notes.json
```

No external database is required.

---

## Configuration

Toolkit uses `settings.ini` for persistent configuration.

Example:

```ini
[BASE]
log = false

[DIRS]
working_dir = ./

[ARCHITECTURE]
active = ../active
complete = ../complete
tests = ../tests
```

The configuration system converts stored values into appropriate Python types when loading settings.

The GUI can be used to modify supported settings without manually editing the configuration file.

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

---

## Requirements

* Python 3.x
* Tkinter

No external database or web service is required for the core application.

Optional functionality may depend on external programs being installed and available in the system `PATH`, for example:

* Git
* Python / pip
* VS Code

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
* allowing new features to be added without significantly changing the existing core.

The application is intentionally lightweight and modular.

---

## Status

**Work in progress.**

Toolkit is an actively evolving personal project. Features, interfaces, project structure, and configuration options may change as new utilities are developed.

Some components are experimental and may be redesigned or replaced.

---

## Author

Created by  **Markus** .
