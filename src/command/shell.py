import subprocess
from jinja2 import Environment, StrictUndefined

_env = Environment(undefined=StrictUndefined, autoescape=False)

class ShellCommand:
    def __init__(self, name, cmd, redo_cmd="", undo_cmd="", description=""):
        self.name = name
        self.templates = {
            "do": _env.from_string(cmd),
            "redo": _env.from_string(redo_cmd or cmd),
            "undo": _env.from_string(undo_cmd) if undo_cmd else None,
        }
        self.description = description

    def build(self, action: str, context: dict) -> str:
        tpl = self.templates.get(action)
        if not tpl:
            return ""
        return tpl.render(**context)

    def run(self, cmd: str):
        if not cmd:
            return {"stdout": "", "stderr": "", "rc": 0}
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return {"stdout": p.stdout, "stderr": p.stderr, "rc": p.returncode}
