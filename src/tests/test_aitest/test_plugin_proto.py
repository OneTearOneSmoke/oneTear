"""Plugin 协议（JSON over stdio）单测。"""
import json
import os
import subprocess
import sys

import pytest


def _server_args():
    return [sys.executable, "-m", "aitest.plugin_proto.server"]


def _talk(req: dict, *, dryrun: bool = False) -> dict:
    args = _server_args() + (["--dryrun"] if dryrun else [])
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate(
        (json.dumps(req) + "\n").encode("utf-8"),
        timeout=10,
    )
    if p.returncode != 0:
        raise RuntimeError(f"server died: rc={p.returncode} stderr={err.decode()[:300]}")
    line = out.decode("utf-8").strip().splitlines()[0]
    return json.loads(line)


def test_protocol_manifest():
    resp = _talk({"id": "m1", "op": "manifest"})
    assert resp["ok"] is True
    out = resp["output"]
    assert "shell.run" in out["commands"]
    assert "python.eval" in out["commands"]
    assert "eq" in out["assertors"]
    assert out["dryrun"] is False


def test_protocol_manifest_dryrun():
    resp = _talk({"id": "m1", "op": "manifest"}, dryrun=True)
    assert resp["ok"] is True
    assert resp["output"]["dryrun"] is True


def test_protocol_invoke_shell_run():
    resp = _talk({
        "id": "i1", "op": "invoke",
        "cmd": "shell.run",
        "args": {"cmd": "echo proto-test"},
        "ctx": {},
    })
    assert resp["ok"] is True, resp
    assert "proto-test" in resp["output"]["stdout"]


def test_protocol_invoke_dryrun_no_side_effect():
    # 真实 shell 会 rm -rf，mock 必须不执行
    resp = _talk({
        "id": "i2", "op": "invoke",
        "cmd": "shell.run",
        "args": {"cmd": "rm -rf /tmp/should-not-exist"},
        "ctx": {},
    }, dryrun=True)
    assert resp["ok"] is True
    assert resp["output"].get("mock") is True
    assert "should-not-exist" in resp["output"]["stdout"]
    # 文件系统未被删除
    assert os.path.exists("/tmp")  # 还存在


def test_protocol_invoke_unknown_cmd():
    resp = _talk({
        "id": "i3", "op": "invoke",
        "cmd": "nonexistent.cmd",
        "args": {},
        "ctx": {},
    })
    assert resp["ok"] is False
    assert resp["error"]["code"] == "UNKNOWN_CMD"


def test_protocol_assert_pass():
    resp = _talk({
        "id": "a1", "op": "assert",
        "assertor": "eq",
        "args": {"value": 1, "expect": 1},
        "ctx": {},
    })
    assert resp["ok"] is True
    assert resp["output"]["passed"] is True


def test_protocol_assert_fail():
    resp = _talk({
        "id": "a2", "op": "assert",
        "assertor": "eq",
        "args": {"value": 1, "expect": 2},
        "ctx": {},
    })
    assert resp["ok"] is True
    assert resp["output"]["passed"] is False
    assert "value" in resp["output"]["error"]


def test_protocol_unknown_op():
    resp = _talk({"id": "x", "op": "wat"})
    assert resp["ok"] is False
    assert resp["error"]["code"] == "UNKNOWN_OP"


def test_client_roundtrip():
    """PluginClient 端到端调用。"""
    from aitest.plugin_proto.client import PluginClient
    with PluginClient(_server_args(), timeout=5) as c:
        m = c.manifest()
        assert "shell.run" in m["commands"]
        out = c.invoke("shell.run", {"cmd": "echo client-test"}, {})
        assert "client-test" in out["output"]["stdout"]
        # 错误命令
        bad = c.invoke("no.such.cmd", {}, {})
        assert bad["ok"] is False


def test_client_dryrun():
    from aitest.plugin_proto.client import PluginClient
    with PluginClient(_server_args() + ["--dryrun"], timeout=5) as c:
        out = c.invoke("shell.run", {"cmd": "rm -rf /tmp/never-created"}, {})
        assert out["ok"] is True
        assert out["output"].get("mock") is True
