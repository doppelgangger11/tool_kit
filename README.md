# Toolkit

Personal Python toolkit for automating routine tasks, managing projects and providing a simple GUI interface.

## Features

* Project initialization
* Task/project activation
* Configuration management via `settings.ini`
* Optional logging
* CLI interface
* GUI interface based on Tkinter
* Modular structure for adding new utilities and scripts

## Project structure

```text
Toolkit/
├── main.py
├── settings.ini
│
├── scripts/
│   ├── init.py
│   ├── activation_new_task.py
│   └── settings_manager.py
│
├── interface/
│   └── open_settings_util.py
│
└── logs/
```

### `main.py`

Main entry point of the application.

Responsible for:

* starting the Toolkit;
* processing CLI arguments;
* launching the GUI;
* loading configuration;
* starting required modules.

### `scripts/`

Contains the main application logic.

* `init.py` — project/environment initialization.
* `activation_new_task.py` — creation and activation of new tasks/projects.
* `settings_manager.py` — reading and writing configuration.

### `interface/`

Contains the graphical interface.

* `open_settings_util.py` — settings window and GUI-related configuration management.

## Configuration

The Toolkit uses `settings.ini` for persistent configuration.

Example:

```ini
[BASE]
log = false

[DIRS]
working_dir = ./
```

Settings are automatically converted to Python types when they are loaded.

## Running

### GUI

```bash
python main.py
```

### CLI

The application also supports command-line arguments.

```bash
python main.py --help
```

Available options may include:

```text
-i, --interface    Launch GUI interface
--log              Enable logging
```

## Requirements

* Python 3.x
* Tkinter

No external database or web service is required.

## Purpose

The project is primarily a personal development toolkit.

Its main goals are:

* reduce repetitive work;
* provide reusable utilities;
* experiment with Python architecture and GUI development;
* keep frequently used automation routines in one place.

## Status

**Work in progress.**

The project structure and functionality may change as new utilities are added.

## Author

Created by Markus.
