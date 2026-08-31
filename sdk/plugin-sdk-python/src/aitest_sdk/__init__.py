"""aitest_sdk —— Python 插件 SDK 骨架

关联设计：[`docs/architecture-v3-modules.md §7`](sdk)
"""
from __future__ import annotations

from typing import Any, Callable


class PluginServer:
    """插件服务端骨架。

    装饰器用法：

        server = PluginServer(name="sort", version="0.1.0")

        @server.command("sort")
        def sort_ints(args: dict) -> dict:
            return {"sorted": sorted(args["input"])}

        server.serve()
    """

    def __init__(self, name: str, version: str = "0.1.0"):
        self._name = name
        self._version = version
        self._commands: dict[str, Callable[[dict], Any]] = {}
        self._assertors: dict[str, Callable[[Any, dict], tuple[bool, str]]] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    def command(self, name: str) -> Callable:
        """装饰器：注册命令处理器。"""

        def deco(fn: Callable[[dict], Any]) -> Callable:
            if name in self._commands:
                raise ValueError(f"duplicate command: {name}")
            self._commands[name] = fn
            return fn

        return deco

    def assertor(self, name: str) -> Callable:
        """装饰器：注册断言器。返回 (passed, message)。"""

        def deco(fn: Callable[[Any, dict], tuple[bool, str]]) -> Callable:
            if name in self._assertors:
                raise ValueError(f"duplicate assertor: {name}")
            self._assertors[name] = fn
            return fn

        return deco

    def serve(self, addr: str = "0.0.0.0:50051") -> None:  # pragma: no cover
        """启动 gRPC server（骨架：仅打印 manifest）。"""
        print(f"[skeleton] plugin ready: {self._name}@{self._version} on {addr}")
        print(f"  commands: {list(self._commands)}")
        print(f"  assertors: {list(self._assertors)}")
        # TODO S1: 真实 grpc.server


__all__ = ["PluginServer"]
