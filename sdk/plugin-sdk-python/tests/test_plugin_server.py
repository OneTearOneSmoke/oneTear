"""PluginServer 单测。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让本地 src/ 可导入
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aitest_sdk import PluginServer  # noqa: E402


def test_register_command():
    server = PluginServer(name="sort", version="0.1.0")

    @server.command("sort_ints")
    def sort_ints(args):
        return {"sorted": sorted(args["input"])}

    assert "sort_ints" in server._commands
    assert server._commands["sort_ints"]({"input": [3, 1, 2]}) == {"sorted": [1, 2, 3]}


def test_register_assertor_pass_and_fail():
    server = PluginServer(name="eq", version="0.1.0")

    @server.assertor("eq")
    def eq(value, spec):
        return (value == spec["expect"], f"{value} == {spec['expect']}")

    passed, msg = server._assertors["eq"](1, {"expect": 1})
    assert passed is True
    assert msg == "1 == 1"

    passed, msg = server._assertors["eq"](1, {"expect": 2})
    assert passed is False


def test_duplicate_command_raises():
    server = PluginServer(name="x", version="0.1.0")

    @server.command("dup")
    def a(args):
        return args

    with pytest.raises(ValueError, match="duplicate command"):

        @server.command("dup")
        def b(args):
            return args


def test_duplicate_assertor_raises():
    server = PluginServer(name="x", version="0.1.0")

    @server.assertor("dup")
    def a(v, s):
        return (True, "")

    with pytest.raises(ValueError, match="duplicate assertor"):

        @server.assertor("dup")
        def b(v, s):
            return (True, "")


def test_server_metadata():
    server = PluginServer(name="meta", version="1.2.3")
    assert server.name == "meta"
    assert server.version == "1.2.3"


def test_serve_skeleton_does_not_raise(capsys):
    """Sprint 1 前的骨架：serve() 只打印 manifest。"""
    server = PluginServer(name="svc", version="0.0.1")

    @server.command("noop")
    def noop(args):
        return {"echo": args}

    server.serve()  # 不抛异常
    captured = capsys.readouterr()
    assert "svc@0.0.1" in captured.out
    assert "noop" in captured.out
