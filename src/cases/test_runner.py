from pathlib import Path

import pytest

from assertor.contains import ContainsAsserter
from command.shell import ShellCommand
from command.registry import CommandRegistry
from core.engine import ExecutionEngine
from core.loader import load_testcases
from main import load_default_commands
from domain.hooks import Hooks
from domain.step import Step
from domain.testcase import TestCase as DomainTestCase
from observer.logger import LoggerObserver


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _build_engine_and_cases():
    root = _project_root()
    cmds = CommandRegistry()
    cmds.load_dir(str(root / "conf" / "command"))

    engine = ExecutionEngine(cmds, observers=[LoggerObserver(base_dir=str(root / "logs"))])
    cases = load_testcases(str(root / "conf" / "testcases"), cmds)
    return engine, cases


def test_load_testcases_and_expand_matrix():
    _, cases = _build_engine_and_cases()
    assert len(cases) == 1

    expanded = list(cases[0].expand())
    assert len(expanded) == 2
    assert expanded[0]["node_count"] == 2
    assert expanded[1]["node_count"] == 3


def test_file_ops_testcase_runs_successfully():
    engine, cases = _build_engine_and_cases()
    engine.run(cases[0])


def test_eventually_uses_redo_command():
    step = Step(
        "retry_step",
        ShellCommand(
            name="retry_cmd",
            cmd="echo status=pending",
            redo_cmd="echo status=ready",
        ),
        ContainsAsserter("status=ready", eventually=True, timeout=2),
    )
    testcase = DomainTestCase(
        name="retry_case",
        matrix={},
        context={},
        steps=[step],
        hooks=Hooks(),
    )
    engine = ExecutionEngine(cmd_registry={})
    engine.run(testcase)


def test_eventually_fails_when_max_retries_exceeded():
    step = Step(
        "retry_fail_step",
        ShellCommand(
            name="retry_fail_cmd",
            cmd="echo status=pending",
            redo_cmd="echo status=pending",
        ),
        ContainsAsserter("status=ready", eventually=True, timeout=5, interval=0, max_retries=2),
    )
    testcase = DomainTestCase(
        name="retry_fail_case",
        matrix={},
        context={},
        steps=[step],
        hooks=Hooks(),
    )
    engine = ExecutionEngine(cmd_registry={})
    with pytest.raises(AssertionError):
        engine.run(testcase)


def test_retry_defaults_are_applied():
    step = Step(
        "retry_defaults_step",
        ShellCommand(
            name="retry_defaults_cmd",
            cmd="echo status=pending",
            redo_cmd="echo status=ready",
        ),
        ContainsAsserter("status=ready", eventually=True, timeout=5, interval=1, max_retries=0),
    )
    testcase = DomainTestCase(
        name="retry_defaults_case",
        matrix={},
        context={},
        steps=[step],
        hooks=Hooks(),
    )
    engine = ExecutionEngine(
        cmd_registry={},
        retry_defaults={"timeout": 1, "interval": 0, "max_retries": 1},
    )
    engine.run(testcase)


def test_step_retry_overrides_defaults():
    step = Step(
        "retry_override_step",
        ShellCommand(
            name="retry_override_cmd",
            cmd="echo status=pending",
            redo_cmd="echo status=ready",
        ),
        ContainsAsserter("status=ready", eventually=True, timeout=5, interval=0, max_retries=5),
        retry={"max_retries": 0, "interval": 0},
    )
    testcase = DomainTestCase(
        name="retry_override_case",
        matrix={},
        context={},
        steps=[step],
        hooks=Hooks(),
    )
    engine = ExecutionEngine(
        cmd_registry={},
        retry_defaults={"timeout": 1, "interval": 0, "max_retries": 2},
    )
    with pytest.raises(AssertionError):
        engine.run(testcase)


def test_registry_can_register_custom_executor(tmp_path):
    class CustomExecutor:
        def __init__(self, name, cmd, description=""):
            self.name = name
            self.cmd = cmd
            self.description = description

        def build(self, action, context):
            return self.cmd

        def run(self, cmd):
            return {"stdout": cmd, "stderr": "", "rc": 0}

    conf = tmp_path / "commands.yaml"
    conf.write_text(
        "- name: custom_cmd\n"
        "  type: custom\n"
        "  cmd: \"echo custom\"\n"
        "  description: \"custom\"\n",
        encoding="utf-8",
    )

    registry = CommandRegistry()
    registry.register_executor("custom", CustomExecutor)
    registry.load_dir(str(tmp_path))

    loaded = registry.get("custom_cmd")
    assert isinstance(loaded, CustomExecutor)
    assert loaded.build("do", {}) == "echo custom"


def test_undo_command_runs_when_step_fails():
    class FailingCommand:
        def __init__(self):
            self.executed = []
            self.name = "failing_command"

        def build(self, action, context):
            return action

        def run(self, cmd):
            self.executed.append(cmd)
            if cmd == "do":
                raise RuntimeError("boom")
            return {"stdout": "", "stderr": "", "rc": 0}

    cmd = FailingCommand()
    step = Step("failing_step", cmd)
    testcase = DomainTestCase(
        name="undo_case",
        matrix={},
        context={},
        steps=[step],
        hooks=Hooks(),
    )
    engine = ExecutionEngine(cmd_registry={})

    with pytest.raises(RuntimeError):
        engine.run(testcase)

    assert cmd.executed == ["do", "undo"]


def test_return_code_assertion_passes():
    step = Step(
        "rc_ok_step",
        ShellCommand(name="rc_ok_cmd", cmd="sh -c 'exit 0'"),
        ContainsAsserter(None, expected_rc=0),
    )
    testcase = DomainTestCase(
        name="rc_ok_case",
        matrix={},
        context={},
        steps=[step],
        hooks=Hooks(),
    )
    engine = ExecutionEngine(cmd_registry={})
    engine.run(testcase)


def test_return_code_assertion_fails():
    step = Step(
        "rc_fail_step",
        ShellCommand(name="rc_fail_cmd", cmd="sh -c 'exit 1'"),
        ContainsAsserter(None, expected_rc=0),
    )
    testcase = DomainTestCase(
        name="rc_fail_case",
        matrix={},
        context={},
        steps=[step],
        hooks=Hooks(),
    )
    engine = ExecutionEngine(cmd_registry={})
    with pytest.raises(AssertionError):
        engine.run(testcase)


def test_eventually_return_code_uses_redo_command():
    class RcFlipCommand:
        def __init__(self):
            self.name = "rc_flip_cmd"

        def build(self, action, context):
            return action

        def run(self, cmd):
            if cmd == "do":
                return {"stdout": "", "stderr": "", "rc": 1}
            return {"stdout": "", "stderr": "", "rc": 0}

    step = Step(
        "rc_eventually_step",
        RcFlipCommand(),
        ContainsAsserter(None, eventually=True, timeout=2, interval=0, max_retries=2, expected_rc=0),
    )
    testcase = DomainTestCase(
        name="rc_eventually_case",
        matrix={},
        context={},
        steps=[step],
        hooks=Hooks(),
    )
    engine = ExecutionEngine(cmd_registry={})
    engine.run(testcase)


def test_load_default_commands_supports_both_directories(tmp_path):
    (tmp_path / "conf" / "command").mkdir(parents=True)
    (tmp_path / "conf" / "commands").mkdir(parents=True)

    (tmp_path / "conf" / "command" / "a.yaml").write_text(
        "- name: cmd_a\n"
        "  type: shell\n"
        "  cmd: \"echo a\"\n",
        encoding="utf-8",
    )
    (tmp_path / "conf" / "commands" / "b.yaml").write_text(
        "- name: cmd_b\n"
        "  type: shell\n"
        "  cmd: \"echo b\"\n",
        encoding="utf-8",
    )

    registry = CommandRegistry()
    load_default_commands(registry, base_dir=str(tmp_path))

    assert registry.get("cmd_a").name == "cmd_a"
    assert registry.get("cmd_b").name == "cmd_b"


def test_hook_cmd_ref_dict_is_supported(tmp_path):
    cmd_dir = tmp_path / "commands"
    case_dir = tmp_path / "cases"
    cmd_dir.mkdir(parents=True)
    case_dir.mkdir(parents=True)

    (cmd_dir / "commands.yaml").write_text(
        "- name: hook_echo\n"
        "  type: shell\n"
        "  cmd: \"echo hook start\"\n"
        "- name: create_file\n"
        "  type: shell\n"
        "  cmd: \"touch {{filename}}\"\n"
        "- name: delete_file\n"
        "  type: shell\n"
        "  cmd: \"rm -f {{filename}}\"\n",
        encoding="utf-8",
    )
    (case_dir / "hook_case.yaml").write_text(
        "name: hook_case\n"
        "context:\n"
        "  filename: \"/tmp/hook_case.txt\"\n"
        "steps:\n"
        "  - name: create_file\n"
        "    cmd_ref: create_file\n"
        "  - name: delete_file\n"
        "    cmd_ref: delete_file\n"
        "hooks:\n"
        "  before:\n"
        "    - cmd_ref: hook_echo\n",
        encoding="utf-8",
    )

    registry = CommandRegistry()
    registry.load_dir(str(cmd_dir))
    cases = load_testcases(str(case_dir), registry)
    engine = ExecutionEngine(cmd_registry=registry)
    engine.run(cases[0])
