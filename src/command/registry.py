import yaml
from pathlib import Path

from command.shell import ShellCommand
from command.sql.postgres import PostgresSQLCommand


class CommandRegistry:
    def __init__(self):
        self._cmds = {}

    def load_dir(self, path: str):
        path = Path(path)
        for yml in path.rglob("*.yaml"):
            self._load_file(yml)

    def _load_file(self, file: Path):
        with open(file) as f:
            items = yaml.safe_load(f) or []

        for item in items:
            cmd = self._build_command(item)
            self._cmds[cmd.name] = cmd

    def _build_command(self, cfg: dict):
        ctype = cfg["type"]

        if ctype == "shell":
            return ShellCommand(
                name=cfg["name"],
                cmd=cfg["cmd"],
                redo_cmd=cfg.get("redo_cmd", ""),
                undo_cmd=cfg.get("undo_cmd", ""),
                description=cfg.get("description", ""),
            )

        if ctype == "sql":
            db = cfg["db"]
            if db == "postgres":
                return PostgresSQLCommand(
                    name=cfg["name"],
                    sql=cfg["sql"],
                    description=cfg.get("description", ""),
                )

            raise ValueError(f"unsupported sql db: {db}")

        raise ValueError(f"unsupported command type: {ctype}")

    def get(self, name: str):
        return self._cmds[name]
