import yaml
import inspect
from pathlib import Path

from command.shell import ShellCommand
from command.sql.postgres import PostgresSQLCommand


class CommandRegistry:
    def __init__(self):
        self._cmds = {}
        self._executors = {
            "shell": ShellCommand,
            "sql:postgres": PostgresSQLCommand,
        }

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
            executor_cls = self._executors["shell"]
            return executor_cls(
                name=cfg["name"],
                cmd=cfg["cmd"],
                redo_cmd=cfg.get("redo_cmd", ""),
                undo_cmd=cfg.get("undo_cmd", ""),
                description=cfg.get("description", ""),
            )

        if ctype == "sql":
            db = cfg["db"]
            key = f"sql:{db}"
            if key in self._executors:
                executor_cls = self._executors[key]
                return executor_cls(
                    name=cfg["name"],
                    sql=cfg["sql"],
                    description=cfg.get("description", ""),
                )

            raise ValueError(f"unsupported sql db: {db}")

        if ctype in self._executors:
            executor_cls = self._executors[ctype]
            kwargs = self._filter_supported_kwargs(executor_cls, cfg)
            return executor_cls(**kwargs)

        raise ValueError(f"unsupported command type: {ctype}")

    def get(self, name: str):
        return self._cmds[name]

    def register_executor(self, type_name: str, executor_cls):
        self._executors[type_name] = executor_cls

    def _filter_supported_kwargs(self, executor_cls, cfg: dict):
        sig = inspect.signature(executor_cls.__init__)
        supported = set(sig.parameters.keys()) - {"self"}
        return {k: v for k, v in cfg.items() if k in supported}
