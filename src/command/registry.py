import yaml
from pathlib import Path
from command.shell import ShellCommand

class CommandRegistry:
    def __init__(self):
        self._defs = {}

    def load_dir(self, path: str):
        """
        扫描目录下所有 .yaml 文件并加载命令
        """
        path = Path(path)
        if not path.exists() or not path.is_dir():
            raise ValueError(f"Command path {path} 不存在或不是目录")

        for file in path.glob("*.yaml"):
            with open(file) as f:
                items = yaml.safe_load(f)

            if not items:
                continue

            for c in items:
                if c["type"] == "shell":
                    self._defs[c["name"]] = ShellCommand(
                        c["name"],
                        c["cmd"],
                        c.get("redo_cmd", ""),
                        c.get("undo_cmd", ""),
                        c.get("description", "")
                    )

    def get(self, name: str):
        return self._defs[name]
