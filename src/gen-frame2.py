#!/usr/bin/env python3
import os
from pathlib import Path

BASE_DIR = Path.cwd()

DIRS = [
    "assertor",
    "command",
    "conf/commands",
    "conf/testcases",
    "core",
    "domain",
    "observer",
    "logs",
    "cases",
]

FILES = {
    # ---------------- assertor ----------------
    "assertor/assertor.py": '''import time
from jinja2 import Template

class Assertor:
    def check(self, result, expect, context):
        if not expect:
            return
        contains = expect.get("contains")
        eventually = expect.get("eventually")
        if contains:
            contains = Template(contains).render(**context)
        if eventually:
            timeout = float(eventually)
            start = time.time()
            while True:
                if contains in result["stdout"]:
                    return
                if time.time() - start > timeout:
                    raise AssertionError(f"Eventually timeout: expect [{contains}], got [{result['stdout']}]")
                time.sleep(0.5)
        else:
            if contains and contains not in result["stdout"]:
                raise AssertionError(f"expect contains [{contains}], got [{result['stdout']}]")
''',

    # ---------------- command ----------------
    "command/shell.py": '''import subprocess
from jinja2 import Environment, StrictUndefined
import time

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
''',

    "command/sql.py": '''import subprocess
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
''',

    "command/ssh.py": '''import subprocess
from jinja2 import Environment, StrictUndefined
import time

_env = Environment(undefined=StrictUndefined, autoescape=False)

class SSHCommand:
    def __init__(self, name, cmd, redo_cmd="", undo_cmd="", description="", ssh_host="127.0.0.1", ssh_user=None):
        self.name = name
        self.cmd = cmd
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
''',

    "command/mock.py": '''class MockCommand:
    def __init__(self, name):
        self.name = name

    def build(self, template, context):
        return f"mocked {self.name}"

    def run(self, cmd, context, expect=None):
        print(f"[MOCK RUN] {cmd} with context {context} expect {expect}")
        return {"stdout": "mocked output", "stderr": "", "rc": 0}
''',

    # ---------------- core ----------------
    "core/node.py": '''from jinja2 import Template
class ExecutionNode:
    def __init__(self, name, executor, cmd_template, expect=None):
        self.name = name
        self.executor = executor
        self.cmd_template = cmd_template
        self.expect = expect or {}

    def run(self, context):
        cmd = self.executor.build(self.cmd_template, context)
        # 渲染 expect 中的 {{}} 变量
        rendered_expect = {}
        for k,v in self.expect.items():
            if isinstance(v, str):
                rendered_expect[k] = Template(v).render(**context)
            else:
                rendered_expect[k] = v
        return self.executor.run(cmd, context, expect=rendered_expect)
''',

    "core/command_registry.py": '''import yaml
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
''',

    "core/testcase_registry.py": '''import yaml
from pathlib import Path
from domain.testcase import TestCase

class TestCaseRegistry:
    def __init__(self):
        self._cases = []

    def load_dir(self, path):
        path = Path(path)
        if not path.exists() or not path.is_dir():
            raise ValueError(f"TestCase path {path} 不存在或不是目录")
        for file in path.glob("*.yaml"):
            self.load_file(file)

    def load_file(self, path):
        with open(path) as f:
            data = yaml.safe_load(f)
        self._cases.append(TestCase.from_dict(data))

    def all(self):
        return self._cases
''',

    "core/engine.py": '''class ExecutionEngine:
    def __init__(self, observers=None, command_registry=None):
        self.observers = observers or []
        self.command_registry = command_registry

    def run_testcase(self, testcase, context):
        ctx = dict(context)
        failed = False
        try:
            self._notify("testcase_start", testcase, ctx)
            nodes = testcase.get_nodes(self.command_registry)
            for node in nodes:
                self._notify("step_start", testcase, node, ctx)
                result = node.run(ctx)
                ctx["last_stdout"] = result["stdout"]
                ctx["last_stderr"] = result["stderr"]
                ctx["last_rc"] = result["rc"]
                self._notify("step_end", testcase, node, ctx, result)
        except Exception as e:
            failed = True
            self._notify("testcase_error", testcase, ctx, e)
            # on_fail hooks
            for node in nodes:
                if node.name.startswith("hook_onfail"):
                    self._notify("step_start", testcase, node, ctx)
                    node.run(ctx)
                    self._notify("step_end", testcase, node, ctx, {"stdout":"", "stderr":"", "rc":-1})
        finally:
            self._notify("testcase_end", testcase, ctx, not failed)

    def _notify(self, event, *args, **kwargs):
        for obs in self.observers:
            fn = getattr(obs, event, None)
            if callable(fn):
                try:
                    fn(*args, **kwargs)
                except Exception as e:
                    print(f"[ObserverError] {obs.__class__.__name__}.{event}: {e}")
''',

    # ---------------- domain ----------------
    "domain/hooks.py": '''from typing import List, Dict

class Hooks:
    def __init__(self, before=None, after=None, on_fail=None):
        self.before: List[Dict] = before or []
        self.after: List[Dict] = after or []
        self.on_fail: List[Dict] = on_fail or []

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            before=cls._normalize(data.get("before")),
            after=cls._normalize(data.get("after")),
            on_fail=cls._normalize(data.get("on_fail")),
        )

    @staticmethod
    def _normalize(items):
        if not items:
            return []
        normalized = []
        for item in items:
            if isinstance(item, str):
                normalized.append({"cmd": item, "type": "shell"})
            else:
                normalized.append(item)
        return normalized
''',

    "domain/testcase.py": '''import itertools
from domain.hooks import Hooks
from core.node import ExecutionNode

class TestCase:
    def __init__(self, name, matrix=None, context=None, steps=None, hooks: Hooks=None):
        self.name = name
        self.matrix = matrix or {}
        self.context = context or {}
        self.steps = steps or []
        self.hooks = hooks or Hooks()

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            name=data["name"],
            matrix=data.get("matrix"),
            context=data.get("context"),
            steps=data.get("steps"),
            hooks=Hooks.from_dict(data.get("hooks", {}))
        )

    def expand(self):
        if not self.matrix:
            yield dict(self.context)
            return
        keys = list(self.matrix.keys())
        for values in itertools.product(*self.matrix.values()):
            ctx = dict(self.context)
            ctx.update(dict(zip(keys, values)))
            yield ctx

    def get_nodes(self, command_registry):
        nodes = []
        for hook in self.hooks.before:
            cmd_str = hook.get("cmd")
            cmd_type = hook.get("type","shell")
            executor = command_registry.get("create_file")
            nodes.append(ExecutionNode(f"hook_before_{cmd_str}", executor, cmd_str))
        for step in self.steps:
            cmd_name = step.get("cmd_ref")
            executor = command_registry.get(cmd_name)
            nodes.append(ExecutionNode(step.get("name"), executor, cmd_name, expect=step.get("expect")))
        for hook in self.hooks.after:
            cmd_str = hook.get("cmd")
            executor = command_registry.get("create_file")
            nodes.append(ExecutionNode(f"hook_after_{cmd_str}", executor, cmd_str))
        for hook in self.hooks.on_fail:
            cmd_str = hook.get("cmd")
            executor = command_registry.get("create_file")
            nodes.append(ExecutionNode(f"hook_onfail_{cmd_str}", executor, cmd_str))
        return nodes
''',

    # ---------------- observer ----------------
    "observer/base.py": '''class BaseObserver:
    def testcase_start(self, testcase, context): pass
    def step_start(self, testcase, node, context): pass
    def step_end(self, testcase, node, context, result): pass
    def testcase_error(self, testcase, context, error): pass
    def testcase_end(self, testcase, context, success): pass
''',

    "observer/logger.py": '''import logging
from pathlib import Path
from observer.base import BaseObserver

class LoggerObserver(BaseObserver):
    def __init__(self, base_dir="logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def _setup_logger(self, testcase):
        self.logger = logging.getLogger(testcase.name)
        self.logger.setLevel(logging.INFO)
        fh = logging.FileHandler(self.base_dir / f"{testcase.name}.log")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.handlers = [fh]

    def testcase_start(self, testcase, context):
        self._setup_logger(testcase)
        self.logger.info(f"TESTCASE START context={context}")

    def step_start(self, testcase, node, context):
        self.logger.info(f"[{node.name}] START context={context}")

    def step_end(self, testcase, node, context, result):
        self.logger.info(f"[{node.name}] END rc={result['rc']} stdout={result['stdout']} stderr={result['stderr']}")

    def testcase_error(self, testcase, context, error):
        self.logger.error(f"ERROR: {error}")

    def testcase_end(self, testcase, context, success):
        self.logger.info(f"TESTCASE END success={success}")
''',

    "observer/allure_observer.py": '''import allure
from observer.base import BaseObserver

class AllureObserver(BaseObserver):
    def testcase_start(self, testcase, context):
        allure.dynamic.feature(testcase.name)

    def step_start(self, testcase, node, context):
        self.current_step = allure.step(f"{node.name} | context={context}")
        self.current_step.__enter__()

    def step_end(self, testcase, node, context, result):
        self.current_step.__exit__(None, None, None)

    def testcase_error(self, testcase, context, error):
        allure.attach(str(error), name="error", attachment_type=allure.attachment_type.TEXT)

    def testcase_end(self, testcase, context, success):
        pass
''',

    # ---------------- conf ----------------
    "conf/commands/commands.yaml": '''- name: create_file
  cmd: "touch {{filename}}"
  type: shell
  redo_cmd: "touch {{filename}}"
  undo_cmd: "rm -f {{filename}}"
  description: "创建文件"
- name: list_file
  cmd: "ls {{filename}}"
  type: shell
  redo_cmd: "ls {{filename}}"
  undo_cmd: ""
  description: "列出文件"
- name: delete_file
  cmd: "rm -f {{filename}}"
  type: shell
  redo_cmd: "rm -f {{filename}}"
  undo_cmd: "touch {{filename}}"
  description: "删除文件"
''',

    "conf/testcases/file_ops.yaml": '''name: file_operations_test
matrix:
  pg_version: [15]
  node_count: [3]
context:
  filename: "/tmp/demo_test_file.txt"
steps:
  - name: create_file
    cmd_ref: create_file
    expect:
      contains: ""
  - name: list_file
    cmd_ref: list_file
    expect:
      contains: "{{filename}}"
  - name: delete_file
    cmd_ref: delete_file
    expect:
      contains: ""
hooks:
  before:
    - "echo '开始文件操作测试'"
  after:
    - "echo '文件操作测试结束'"
  on_fail:
    - "echo '文件操作失败'"
''',

    # ---------------- main.py ----------------
    "main.py": '''from core.command_registry import CommandRegistry
from core.testcase_registry import TestCaseRegistry
from core.engine import ExecutionEngine
from observer.logger import LoggerObserver

def main():
    cmds = CommandRegistry()
    cmds.load_dir("conf/commands")

    cases = TestCaseRegistry()
    cases.load_dir("conf/testcases")

    observers = [LoggerObserver()]

    engine = ExecutionEngine(observers, cmds)

    for case in cases.all():
        for ctx in case.expand():
            engine.run_testcase(case, ctx)

if __name__ == "__main__":
    main()
''',
}

# ================ create directories ================
for d in DIRS:
    Path(BASE_DIR / d).mkdir(parents=True, exist_ok=True)

# ================ create files ================
for file_path, content in FILES.items():
    full_path = BASE_DIR / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("全量框架生成完成！可直接执行 main.py 或者使用 pytest 运行 cases")
