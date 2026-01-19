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

    def _check_return_code(self,expected_rc, actual_rc, stdout, stderr, cmd):
        if expected_rc is None:
            return

        # 支持 list / 单值
        if isinstance(expected_rc, (list, tuple, set)):
            ok = actual_rc in expected_rc
        else:
            ok = actual_rc == expected_rc

        if not ok:
            raise AssertionError(
                f"Command return code mismatch:\n"
                f"  cmd: {cmd}\n"
                f"  expected rc: {expected_rc}\n"
                f"  actual rc: {actual_rc}\n"
                f"  stdout: {stdout}\n"
                f"  stderr: {stderr}"
            )

    def run(self, cmd, context, expect=None):
        if not cmd:
            return {"stdout": "", "stderr": "", "rc": 0}
        contains = expect.get("contains") if expect else None
        if contains:
            from jinja2 import Template
            contains = Template(contains).render(**context)
        eventually = float(expect.get("eventually")) if expect and expect.get("eventually") else None
        expected_rc = None
        if expect:
            expected_rc = expect.get("return_code", expect.get("rc"))
        start = time.time()
        while True:
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            stdout, stderr, rc = p.stdout, p.stderr, p.returncode
            if eventually:
                if contains is None or contains in stdout:
                    # eventually 命中后，再校验 return_code
                    self._check_return_code(expected_rc, rc, stdout, stderr, cmd)
                    return {"stdout": stdout, "stderr": stderr, "rc": rc}
                if time.time() - start > eventually:
                    raise AssertionError(f"Eventually timeout for shell: expect [{contains}], got [{stdout}]")
                time.sleep(0.5)
                continue

            self._check_return_code(expected_rc, rc, stdout, stderr, cmd)
            return {"stdout": stdout, "stderr": stderr, "rc": rc}
