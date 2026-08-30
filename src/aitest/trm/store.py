"""TRM 视角的 store 包装。

EXF 自己有 `core.store.ResultStore`（写为主），TRM 只读。
这里不强制依赖 EXF，方便在 v1.0 切换到 ClickHouse / Postgres 后只换 Adapter。

设计要点：
  - 只暴露 TRM 需要的查询接口（list_recent / list_by_case / list_by_plan）
  - 内部统一返回 dict（而非 EXF 的 ResultRow），降低跨模块耦合
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


def to_dict(r: Any) -> dict:
    """统一 EXF ResultRow / dict → dict。"""
    if isinstance(r, dict):
        return r
    if hasattr(r, "to_dict"):
        return r.to_dict()
    raise TypeError(f"unsupported row type: {type(r)}")


def list_recent(store: Any, limit: int = 1000) -> List[dict]:
    """统一入口：取最近 limit 条结果。"""
    if hasattr(store, "recent"):
        return [to_dict(r) for r in store.recent(limit=limit)]
    if hasattr(store, "list_recent"):
        return [to_dict(r) for r in store.list_recent(limit=limit)]
    raise TypeError("store must implement recent() or list_recent()")


def list_by_plan(store: Any, plan_id: str, limit: int = 100000) -> List[dict]:
    if not hasattr(store, "list_by_plan"):
        raise TypeError("store must implement list_by_plan")
    return [to_dict(r) for r in store.list_by_plan(plan_id, limit=limit)]


def list_by_case(store: Any, case_id: str, limit: int = 1000) -> List[dict]:
    if not hasattr(store, "list_by_case"):
        raise TypeError("store must implement list_by_case")
    return [to_dict(r) for r in store.list_by_case(case_id, limit=limit)]
