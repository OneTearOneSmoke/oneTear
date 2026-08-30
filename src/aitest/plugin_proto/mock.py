"""Dryrun mock 插件：仅供 v0.5 dryrun 模式使用。

替换真实 shell / python / llm 调用为本地 mock，避免副作用。
不模拟复杂行为，只保证"逻辑可执行"。

用法：
  --dryrun CLI 模式 → 启动子进程：`python -m aitest.plugin_proto.server --dryrun`
  → 服务端检测到 dryrun=True 时使用 MockPlugin
"""
from __future__ import annotations
import os
import random
import time
from typing import Any, Dict


class MockShell:
    name = "shell.run"
    def run(self, args, ctx):
        cmd = args.get("cmd", "")
        return {"stdout": f"[mock] {cmd}\n", "stderr": "", "rc": 0,
                "mock": True, "echo_cmd": cmd}


class MockPython:
    name = "python.eval"
    def run(self, args, ctx):
        if "expr" in args:
            return {"result": None, "expr": args["expr"], "mock": True}
        target = args.get("call", "")
        with_args = args.get("with")
        if with_args is None:
            return {"result": None, "mock": True, "call": target}
        # 对排序类简单场景，模拟一个"看起来对"的结果
        if isinstance(with_args, list):
            try:
                return {"result": sorted(with_args), "mock": True, "call": target}
            except Exception:
                return {"result": with_args, "mock": True, "call": target}
        return {"result": with_args, "mock": True, "call": target}


class MockLLM:
    name = "llm.query"
    def run(self, args, ctx):
        prompt = args.get("prompt", "")
        return {"text": f"[mock-llm] {prompt[:120]}", "mock": True, "provider": args.get("provider", "echo")}


class MockHttp:
    name = "http.request"
    def run(self, args, ctx):
        url = args.get("url", "")
        return {"status": 200, "headers": {}, "body": {"mock": True, "url": url}, "mock": True}


class MockSeedRng:
    name = "builtin.seed_rng"
    def run(self, args, ctx):
        seed = args.get("seed", 0)
        random.seed(seed)
        ctx.meta["rng_seeded"] = True
        return {"seed": seed, "mock": True}


class MockMakeTmp:
    name = "builtin.make_tmp"
    def run(self, args, ctx):
        path = f"/tmp/aitest-mock-{os.getpid()}-{int(time.time()*1000)}"
        ctx.meta["tmp"] = path
        return {"tmp": path, "mock": True}


class MockCleanTmp:
    name = "builtin.clean_tmp"
    def run(self, args, ctx):
        return {"removed": 0, "mock": True}


# 简单 assertor mock
class MockEq:
    name = "eq"
    def check(self, args, ctx):
        if args.get("value") != args.get("expect"):
            from ..core.errors import AssertFailure
            raise AssertFailure(self.name, f"value={args.get('value')!r} expect={args.get('expect')!r}")


class MockContains:
    name = "contains"
    def check(self, args, ctx):
        if args.get("substr", "") not in (args.get("value", "") or ""):
            from ..core.errors import AssertFailure
            raise AssertFailure(self.name, f"value={args.get('value')!r} not contain {args.get('substr')!r}")


def install_mock(registry) -> None:
    """把 mock 命令/断言装到 registry。"""
    for c in (MockShell, MockPython, MockLLM, MockHttp, MockSeedRng, MockMakeTmp, MockCleanTmp):
        registry.command(instance=c())
    for a in (MockEq, MockContains):
        registry.assertor(instance=a())
