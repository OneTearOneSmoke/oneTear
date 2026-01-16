import subprocess
from jinja2 import Environment, StrictUndefined
import time

_env = Environment(undefined=StrictUndefined, autoescape=False)

class SSHCommand:
    def __init__(self, name, cmd, redo_cmd="", undo_cmd="", description="", ssh_host="127.0.0.1", ssh_user=None):
        self.name = name
        self.cmd = cmd
        self.type = "ssh"
        self.description = description
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user

    def build(self, template, context):
        return _env.from_string(self.cmd).render(**context)

    def run(self, cmd, context, expect=None):
        if not cmd:
            return {"stdout": "", "stderr": "", "rc": 0}
        contains = expect.get("contains") if expect else None
        if contains:
            from jinja2 import Template
            contains = Template(contains).render(**context)
        eventually = float(expect.get("eventually")) if expect and expect.get("eventually") else None
        ssh_prefix = f"{self.ssh_user}@{self.ssh_host}" if self.ssh_user else self.ssh_host
        ssh_cmd = f"ssh {ssh_prefix} '{cmd}'"
        start = time.time()
        while True:
            p = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
            stdout, stderr, rc = p.stdout, p.stderr, p.returncode
            if eventually:
                if contains in stdout:
                    return {"stdout": stdout, "stderr": stderr, "rc": rc}
                if time.time() - start > eventually:
                    raise AssertionError(f"Eventually timeout for SSH: expect [{contains}], got [{stdout}]")
                time.sleep(0.5)
                continue
            return {"stdout": stdout, "stderr": stderr, "rc": rc}
