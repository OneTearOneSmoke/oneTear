"""插件进程间协议（v0.5 JSON over stdio）。

为 v0.8 切换 gRPC 之前的临时方案：
  - 客户端：PluginClient（父进程 / 调度器）
  - 服务端：PluginServer（子进程 / 独立进程）
  - 协议：行分隔 JSON（每行一条消息）

消息格式：
  请求：{"id": "...", "op": "invoke", "cmd": "shell.run", "args": {...}, "ctx": {...}}
  响应：{"id": "...", "ok": true,  "output": {...}, "error": null}
  响应：{"id": "...", "ok": false, "error": {"code":"...","message":"..."}}

启动方式：
  python -m aitest.plugin_proto.server --manifest <yaml> --registry default
"""
from .client import PluginClient
from .server import PluginServer, run_server_from_argv
