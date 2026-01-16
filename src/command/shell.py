import subprocess
from jinja2 import Environment, StrictUndefined
import time

_env = Environment(undefined=StrictUndefined, autoescape=False)

class ShellCommand:
    def __init__(self, name, cmd, redo_cmd="", undo_cmd="", description=""):
        self.name = name
        self.type = "shell"
        self.templates = {
            "do": _env.from_string(cmd),
            "redo": _env.from_string(redo_cmd or cmd),
            "undo": _env.from_string(undo_cmd) if undo_cmd else None,
        }
        self.description = description

    def build(self, template, context):
        return self.templates["do"].render(**context)

    def run(self, cmd, context, expect=None):
        if not cmd:
            return {"stdout": "", "stderr": "", "rc": 0}
        contains = expect.get("contains") if expect else None
        if contains:
            from jinja2 import Template
            contains = Template(contains).render(**context)
        eventually = float(expect.get("eventually")) if expect and expect.get("eventually") else None
        start = time.time()
        while True:
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            stdout, stderr, rc = p.stdout, p.stderr, p.returncode
            if eventually:
                if contains in stdout:
                    return {"stdout": stdout, "stderr": stderr, "rc": rc}
                if time.time() - start > eventually:
                    raise AssertionError(f"Eventually timeout for shell: expect [{contains}], got [{stdout}]")
                time.sleep(0.5)
                continue
            return {"stdout": stdout, "stderr": stderr, "rc": rc}
