from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass
class Command:
    id: str
    group: str
    name: str
    command: str
    parameter: str = ""
    admin: bool = False


class QuickCommandsManager:

    def __init__(self, path: Path):
        self.path = Path(path)

    # ---------------------------------------------------------
    # CONFIG
    # ---------------------------------------------------------

    def _load_config(self):
        config = ConfigParser()
        config.read(self.path, encoding="utf-8")
        return config

    def _save_config(self, config):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with self.path.open(
            "w",
            encoding="utf-8"
        ) as file:
            config.write(file)

    # ---------------------------------------------------------
    # GROUPS
    # ---------------------------------------------------------

    def get_groups(self) -> list[str]:

        config = self._load_config()

        if not config.has_section("GROUPS"):
            return []

        return list(config["GROUPS"].keys())

    def add_group(self, name: str):

        name = name.strip()

        if not name:
            raise ValueError(
                "Group name cannot be empty."
            )

        groups = self.get_groups()

        if name in groups:
            raise ValueError(
                f"Group '{name}' already exists."
            )

        config = self._load_config()

        if not config.has_section("GROUPS"):
            config.add_section("GROUPS")

        config["GROUPS"][name] = name

        self._save_config(config)

    def remove_group(self, name: str):

        config = self._load_config()

        if config.has_section("GROUPS"):
            config.remove_option(
                "GROUPS",
                name
            )

        prefix = f"COMMAND.{name}."

        for section in list(config.sections()):

            if section.startswith(prefix):
                config.remove_section(section)

        self._save_config(config)

    # ---------------------------------------------------------
    # COMMANDS
    # ---------------------------------------------------------

    def get_commands(self) -> list[Command]:

        config = self._load_config()

        commands = []

        for section in config.sections():

            if not section.startswith("COMMAND."):
                continue

            commands.append(
                Command(
                    id=section.removeprefix("COMMAND."),
                    group=config.get(
                        section,
                        "group"
                    ),
                    name=config.get(
                        section,
                        "name"
                    ),
                    command=config.get(
                        section,
                        "command"
                    ),
                    parameter=config.get(
                        section,
                        "parameter",
                        fallback=""
                    ),
                    admin=config.getboolean(
                        section,
                        "admin",
                        fallback=False
                    )
                )
            )

        return commands

    def add_command(
        self,
        group: str,
        name: str,
        command: str,
        parameter: str = "",
        admin: bool = False
    ) -> Command:

        group = group.strip()
        name = name.strip()
        command = command.strip()

        if not group:
            raise ValueError(
                "Group cannot be empty."
            )

        if not name:
            raise ValueError(
                "Command name cannot be empty."
            )

        if not command:
            raise ValueError(
                "Command cannot be empty."
            )

        if group not in self.get_groups():
            raise ValueError(
                f"Group '{group}' does not exist."
            )

        command_id = str(uuid4())

        new_command = Command(
            id=command_id,
            group=group,
            name=name,
            command=command,
            parameter=parameter,
            admin=admin
        )

        config = self._load_config()

        section = f"COMMAND.{command_id}"

        config[section] = {
            "group": group,
            "name": name,
            "command": command,
            "parameter": parameter,
            "admin": str(admin),
        }

        self._save_config(config)

        return new_command

    def update_command(
        self,
        command: Command
    ):

        config = self._load_config()

        section = f"COMMAND.{command.id}"

        if not config.has_section(section):
            raise ValueError(
                "Command does not exist."
            )

        config[section] = {
            "group": command.group,
            "name": command.name,
            "command": command.command,
            "parameter": command.parameter,
            "admin": str(command.admin),
        }

        self._save_config(config)

    def remove_command(
        self,
        command: Command
    ):

        config = self._load_config()

        section = f"COMMAND.{command.id}"

        if config.has_section(section):
            config.remove_section(section)

        self._save_config(config)