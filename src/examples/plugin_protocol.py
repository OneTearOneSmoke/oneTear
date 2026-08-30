"""Examples: 演示 JSON-over-stdio 插件协议 + dryrun 流程。

1. 启动子进程作为插件服务器
2. 客户端通过 stdio JSON-RPC 调用命令/断言
3. 演示 dryrun 模式（mock target）

跑法：
    cd src && python3 -m examples.plugin_protocol
"""
from __future__ import annotations
import os
import subprocess
import sys
import time

from aitest.plugin_proto.client import PluginClient
from aitest.plugin_proto.mock import install_mock
from aitest.core.registry import Registry
from aitest.core.case import Case, CaseStep, CaseAssert
from aitest.core.runner import Runner
from aitest.core.context import Context


SERVER_CMD = [sys.executable, "-m", "aitest.plugin_proto.server"]


def main() -> None:
    print("=== 1) real plugin via stdio (shell.run echo) ===")
    with PluginClient(SERVER_CMD, timeout=10) as c:
        m = c.manifest()
        print(f"  manifest: {len(m['commands'])} commands, {len(m['assertors'])} assertors, dryrun={m['dryrun']}")
        r = c.invoke("shell.run", {"cmd": "echo hello-from-plugin"}, {})
        assert r["ok"], r
        print(f"  shell.run stdout: {r['output']['stdout'].rstrip()}")

    print("\n=== 2) dryrun plugin via stdio (mock shell.run) ===")
    with PluginClient(SERVER_CMD + ["--dryrun"], timeout=10) as c:
        m = c.manifest()
        assert m["dryrun"] is True
        r = c.invoke("shell.run", {"cmd": "rm -rf /tmp/this-should-not-exist"}, {})
        assert r["ok"] and r["output"].get("mock") is True
        print(f"  mock stdout: {r['output']['stdout'].rstrip()}")
        assert os.path.exists("/tmp")  # 真实未受影响

    print("\n=== 3) in-process dryrun with mock registry ===")
    reg = Registry()
    # 加载默认命令 + mock
    from aitest.commands.shell import ShellRun
    from aitest.commands.python import PythonEval
    from aitest.commands.builtin import MakeTmp, CleanTmp, SeedRng
    from aitest.assertors.basic import Eq, Contains, Truthy
    from aitest.providers.echo import EchoProvider
    for c in (ShellRun, PythonEval, MakeTmp, CleanTmp, SeedRng):
        reg.command(instance=c())
    for a in (Eq, Contains, Truthy):
        reg.assertor(instance=a())
    reg.provider(instance=EchoProvider())
    install_mock(reg)  # 覆盖为 mock

    case = Case(
        id="demo.dryrun",
        run=CaseStep(cmd="python.eval", args={"call": "sorted", "with": [3, 1, 2]}),
        asserts=[CaseAssert(name="eq", args={"value": "{{ run.python.eval.result }}", "expect": [1, 2, 3]})],
    )
    runner = Runner(reg)
    result = runner.run_case(case)
    print(f"  status: {result.status} ok={result.ok}")
    assert result.status == "SUCCESS"

    print("\n=== 4) LLM judge with echo provider (real plugin, no network) ===")
    with PluginClient(SERVER_CMD, timeout=10) as c:
        r = c.invoke("llm.query", {"provider": "echo", "prompt": "judge this code: a = 1+1"}, {})
        assert r["ok"]
        print(f"  llm.text: {r['output']['text'][:80]}")

    print("\n[done] all 4 demos passed")


if __name__ == "__main__":
    main()
