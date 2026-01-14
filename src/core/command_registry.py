import yaml
from pathlib import Path
from command.shell import ShellCommand
from command.sql import SQLCommand
from command.ssh import SSHCommand
from command.mock import MockCommand

class CommandRegistry:
    def __init__(self):
        self._commands = {}
        self._executors = {
            "shell": ShellCommand,
            "sql": SQLCommand,
            "ssh": SSHCommand,
            "mock": MockCommand,
        }

    def load_dir(self, path):
        path = Path(path)
        if not path.exists() or not path.is_dir():
            raise ValueError(f"Command path {path} 不存在或不是目录")
        for file in path.glob("*.yaml"):
            self.load_file(file)

    def load_file(self, path):
        with open(path) as f:
            data = yaml.safe_load(f)
        for cmd_cfg in data:
            name = cmd_cfg["name"]
            type_ = cmd_cfg.get("type","shell")
            executor_cls = self._executors[type_]
            kwargs = {k: cmd_cfg.get(k) for k in ["cmd","redo_cmd","undo_cmd","description","db_host","db_name","db_user","ssh_host","ssh_user"] if k in cmd_cfg}
            self._commands[name] = executor_cls(name=name, **kwargs)

    def get(self, name):
        return self._commands[name]
