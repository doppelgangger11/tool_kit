import os
from typing import Any
from pathlib import Path
from configparser import ConfigParser

def read_settings(directory: Path) -> dict[str, dict[str, Any]]:
    if not (directory / "settings.ini").is_file():
        print("Error: File not found")
        print("Used default settings!")
        write_settings(
            directory,
            settings = {
                "BASE": {
                    "log": "False",
                },

                "DIRS": {
                    "working_dir": "",
                    "temp_dir": "../temp",
                    "notes_dir": "./db",
                },

                "PROGRAMS": {},

                "ARCHITECTURE": {},
            }
        )

    config = ConfigParser()
    
    # Preserve original case of option names
    config.optionxform = str
    config.read(directory / "settings.ini")

    settings = {}
    
    for section in config.sections():
        settings[section] = {}
        for setting in config[section]:
            for converter in (
                config.getint,
                config.getfloat,
                config.getboolean,
            ):
                try:
                    settings[section][setting] = converter(
                        section,
                        setting
                    )
                    break
                except ValueError:
                    pass
            else:
                settings[section][setting] = config[section][setting]
    return settings

def write_settings(
    directory: Path,
    settings: dict[str, dict[str, Any]]
) -> None:
    
    config = ConfigParser()

    # Preserve original case of option names
    config.optionxform = str

    for section, values in settings.items():
        config[section] = values

    with open(
        directory / "settings.ini",
        "w",
        encoding="utf-8"
    ) as file:
        config.write(file)