from types import SimpleNamespace

from command.shell import ShellCommand
from command.sql import SQLCommand
from command.ssh import SSHCommand
from domain.hooks import Hooks
from domain.testcase import TestCase as DomainTestCase


class _DummyRegistry:
    def __init__(self, names):
        self._names = names

    def get(self, name):
        if name not in self._names:
            raise KeyError(name)
        return ShellCommand(name=name, cmd=f"echo {name}")


def test_hooks_string_is_normalized_to_cmd_ref():
    hooks = Hooks.from_dict({"before": ["echo_start"]})
    assert hooks.before[0]["cmd_ref"] == "echo_start"


def test_testcase_get_nodes_accepts_legacy_hook_cmd_key():
    testcase = DomainTestCase(
        name="hook_case",
        context={},
        steps=[],
        hooks=Hooks(before=[{"cmd": "echo_start"}]),
    )
    nodes = testcase.get_nodes(_DummyRegistry({"echo_start"}))
    assert len(nodes) == 1
    assert nodes[0].name.startswith("hook_before_echo_start_")


def test_shell_build_respects_template_action():
    cmd = ShellCommand(
        name="sample",
        cmd="echo do",
        redo_cmd="echo redo",
        undo_cmd="echo undo",
    )
    assert cmd.build("do", {}) == "echo do"
    assert cmd.build("redo", {}) == "echo redo"
    assert cmd.build("undo", {}) == "echo undo"


def test_sql_eventually_without_contains_returns_first_result(monkeypatch):
    def _fake_run(*args, **kwargs):
        return SimpleNamespace(stdout="ok", stderr="", returncode=0)

    monkeypatch.setattr("command.sql.subprocess.run", _fake_run)
    cmd = SQLCommand(name="sql_check", cmd="select 1")
    result = cmd.run("select 1", {}, expect={"eventually": "1"})
    assert result["rc"] == 0
    assert result["stdout"] == "ok"


def test_ssh_eventually_without_contains_returns_first_result(monkeypatch):
    def _fake_run(*args, **kwargs):
        return SimpleNamespace(stdout="ok", stderr="", returncode=0)

    monkeypatch.setattr("command.ssh.subprocess.run", _fake_run)
    cmd = SSHCommand(name="ssh_check", cmd="echo hi")
    result = cmd.run("echo hi", {}, expect={"eventually": "1"})
    assert result["rc"] == 0
    assert result["stdout"] == "ok"
