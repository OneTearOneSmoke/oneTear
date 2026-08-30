"""内置插件清单与发现（v0.5 η）。

返回结构：
  PluginMeta {
    name, version, description, commands: [...], assertors: [...]
  }

v1.0 替换为 entry_points（`aitest.plugins` group）。
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List

from .db_sqlite import DB_SQLITE_MANIFEST


@dataclass
class PluginMeta:
    name: str
    version: str
    description: str
    commands: List[str] = field(default_factory=list)
    assertors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


_BUILTINS: Dict[str, PluginMeta] = {
    DB_SQLITE_MANIFEST["name"]: PluginMeta(
        name=DB_SQLITE_MANIFEST["name"],
        version=DB_SQLITE_MANIFEST["version"],
        description=DB_SQLITE_MANIFEST["description"],
        commands=DB_SQLITE_MANIFEST["commands"],
        assertors=DB_SQLITE_MANIFEST["assertors"],
    ),
}


def list_builtin() -> List[PluginMeta]:
    return list(_BUILTINS.values())


def list_manifests() -> List[dict]:
    return [m.to_dict() for m in list_builtin()]


def get(name: str) -> PluginMeta:
    if name not in _BUILTINS:
        raise KeyError(f"unknown plugin: {name}")
    return _BUILTINS[name]
