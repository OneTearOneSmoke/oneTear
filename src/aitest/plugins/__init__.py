"""PLG (Plugin) 子系统 — 真实可执行插件库。

按 [`plugin-system-design.md`](../docs/ai-test/plugin-system-design.md)：

  - 每个插件 = 一组 Command + Assertor + Provider 的集合
  - 通过 stdio JSON 协议被 EXF 调度（plugin_proto/）
  - 单进程可注册多个插件；多进程用 plugin-server 子命令

v0.5 η 原型：
  - db_sqlite : 进程内 SQLite，无需额外依赖
  - discovery : 进程内 plugin 列表（hardcoded 起步，v1.0 接 entry_points）
"""

from .db_sqlite import DB_SQLITE_MANIFEST
from .discovery import list_builtin, list_manifests

__all__ = [
    "DB_SQLITE_MANIFEST",
    "list_builtin",
    "list_manifests",
]
