"""插件服务端：在子进程中跑，把 stdio 当成 RPC 通道。

支持 ops:
  - invoke:  { "cmd": str, "args": dict, "ctx": dict }
  - manifest: 返回插件清单（命令/断言列表）
"""
from __future__ import annotations
import argparse
import sys
import threading
import traceback
from typing import Any, Dict

from .protocol import decode_line, encode, make_request, make_response_ok, make_response_err


def _build_default_registry():
    """构造一个完整命令 + 断言 + Provider 注册表。"""
    from ..core.registry import Registry
    from ..commands.ast_diff import AstDiff
    from ..commands.builtin import CleanTmp, MakeTmp, SeedRng, Sleep
    from ..commands.http import HttpRequest
    from ..commands.llm import LLMQuery
    from ..commands.python import PythonEval
    from ..commands.shell import ShellRun
    from ..assertors.ast_struct import AstStruct
    from ..assertors.basic import Contains, Eq, Ne, Regex, Truthy
    from ..assertors.embedding import EmbeddingSim
    from ..assertors.eventually import Eventually
    from ..assertors.json_schema import JsonSchema
    from ..assertors.llm_judge import LLMJudge
    from ..assertors.property import Property
    from ..providers.echo import EchoProvider
    from ..providers.openai import OpenAIProvider

    reg = Registry()
    for c in (ShellRun, PythonEval, HttpRequest, LLMQuery, AstDiff,
              SeedRng, MakeTmp, CleanTmp, Sleep):
        reg.command(instance=c())
    for a in (Eq, Ne, Contains, Regex, Truthy, JsonSchema, EmbeddingSim,
              LLMJudge, AstStruct, Property, Eventually):
        reg.assertor(instance=a())
    reg.provider(instance=EchoProvider())
    reg.provider(instance=OpenAIProvider())
    return reg


class PluginServer:
    def __init__(self, registry=None, *, dryrun: bool = False) -> None:
        base = registry or _build_default_registry()
        if dryrun:
            # dryrun 模式：把所有可 mock 的命令/断言替换为 mock 实现
            from .mock import install_mock
            install_mock(base)
        self.registry = base
        self.dryrun = dryrun
        self._in = sys.stdin
        self._out = sys.stdout
        self._lock = threading.Lock()

    # ---- 主循环 ----
    def serve_forever(self) -> None:
        for raw in self._in:
            try:
                req = decode_line(raw)
            except Exception as e:  # noqa: BLE001
                self._send_err("bad-request", f"decode: {e}")
                continue
            try:
                resp = self._handle(req)
            except Exception as e:  # noqa: BLE001
                resp = make_response_err(
                    req.get("id", "?"), "INTERNAL",
                    f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
                )
            self._send(resp)

    def _handle(self, req: Dict[str, Any]) -> Dict[str, Any]:
        op = req.get("op")
        rid = req.get("id", "?")
        if op == "manifest":
            return make_response_ok(rid, {
                "commands": self.registry.list_commands(),
                "assertors": self.registry.list_assertors(),
                "providers": self.registry.list_providers(),
                "dryrun": self.dryrun,
            })
        if op == "invoke":
            return self._do_invoke(rid, req)
        if op == "assert":
            return self._do_assert(rid, req)
        return make_response_err(rid, "UNKNOWN_OP", f"unknown op: {op!r}")

    def _do_invoke(self, rid: str, req: Dict[str, Any]) -> Dict[str, Any]:
        cmd_name = req.get("cmd")
        args = req.get("args") or {}
        ctx_data = req.get("ctx") or {}
        try:
            cmd = self.registry.get_command(cmd_name)
        except KeyError as e:
            return make_response_err(rid, "UNKNOWN_CMD", str(e))
        try:
            from ..core.context import Context
            ctx = Context()
            ctx.params = ctx_data.get("params") or {}
            ctx.run = ctx_data.get("run") or {}
            ctx.meta = ctx_data.get("meta") or {}
            ctx.meta["__registry__"] = self.registry
            out = cmd.run(args, ctx)
            return make_response_ok(rid, out or {})
        except Exception as e:  # noqa: BLE001
            return make_response_err(rid, "CMD_FAIL", f"{type(e).__name__}: {e}")

    def _do_assert(self, rid: str, req: Dict[str, Any]) -> Dict[str, Any]:
        an = req.get("assertor")
        args = req.get("args") or {}
        ctx_data = req.get("ctx") or {}
        try:
            ass = self.registry.get_assertor(an)
        except KeyError as e:
            return make_response_err(rid, "UNKNOWN_ASSERT", str(e))
        try:
            from ..core.context import Context
            ctx = Context()
            ctx.params = ctx_data.get("params") or {}
            ctx.run = ctx_data.get("run") or {}
            ctx.meta = ctx_data.get("meta") or {}
            ass.check(args, ctx)
            return make_response_ok(rid, {"passed": True})
        except Exception as e:  # noqa: BLE001
            return make_response_ok(rid, {"passed": False, "error": f"{type(e).__name__}: {e}"})

    # ---- I/O ----
    def _send(self, resp: Dict[str, Any]) -> None:
        with self._lock:
            self._out.buffer.write(encode(resp))
            self._out.buffer.flush()

    def _send_err(self, code: str, message: str) -> None:
        self._send(make_response_err("-", code, message))


def run_server_from_argv(argv=None) -> int:
    p = argparse.ArgumentParser(prog="aitest-plugin-server")
    p.add_argument("--dryrun", action="store_true")
    p.add_argument("--plugin", help="built-in plugin to mount (e.g. db_sqlite)")
    args = p.parse_args(argv)
    registry = _build_registry_for(args.plugin, dryrun=args.dryrun)
    PluginServer(registry=registry, dryrun=args.dryrun).serve_forever()
    return 0


def _build_registry_for(plugin: str | None, *, dryrun: bool = False):
    """根据 --plugin 选择加载器；None = 全量默认注册表。"""
    if plugin is None:
        return None  # 由 PluginServer.__init__ 用默认
    if plugin == "db_sqlite":
        from ..plugins.db_sqlite import build_registry as build_db
        return build_db()
    raise SystemExit(f"unknown built-in plugin: {plugin!r}")



if __name__ == "__main__":
    sys.exit(run_server_from_argv())
