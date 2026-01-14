import subprocess
from jinja2 import Environment, StrictUndefined
import time

_env = Environment(undefined=StrictUndefined, autoescape=False)

class SQLCommand:
    def __init__(self, name, cmd, redo_cmd="", undo_cmd="", description="", db_host="localhost", db_name="postgres", db_user="postgres"):
        self.name = name
        self.cmd = cmd
        self.description = description
        self.db_host = db_host
        self.db_name = db_name
        self.db_user = db_user

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
        start = time.time()
        psql_cmd = f'psql -h {self.db_host} -U {self.db_user} -d {self.db_name} -c "{cmd}"'
        while True:
            p = subprocess.run(psql_cmd, shell=True, capture_output=True, text=True)
            stdout, stderr, rc = p.stdout, p.stderr, p.returncode
            if eventually:
                if contains in stdout:
                    return {"stdout": stdout, "stderr": stderr, "rc": rc}
                if time.time() - start > eventually:
                    raise AssertionError(f"Eventually timeout for SQL: expect [{contains}], got [{stdout}]")
                time.sleep(0.5)
                continue
            return {"stdout": stdout, "stderr": stderr, "rc": rc}
