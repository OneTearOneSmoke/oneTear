"""Analyzer 协议 + 注册表。

TRM 内部所有高阶分析器（Flaky / Baseline / Trend）都实现同一个 Analyzer 接口，
方便 v1.0 接入：
  - ClickHouse 适配器
  - Postgres 适配器
  - 用户自定义外部脚本
  - AI Agent 触发的动态分析器

约束：
  - 每个 Analyzer 是无状态的（state 在 store / 参数里）
  - 入口方法 `run(*, store, **kwargs) -> dict` 返回可 JSON 序列化的结构
  - 不写 store，只读
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


@dataclass
class AnalyzerResult:
    """Analyzer 通用返回包装。"""

    name: str
    summary: str
    data: Dict[str, Any]
    recommendations: List[str]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "summary": self.summary,
            "data": self.data,
            "recommendations": self.recommendations,
        }


class Analyzer(ABC):
    """所有 TRM 高阶分析的抽象基类。"""

    name: str = "abstract"

    @abstractmethod
    def run(self, store: Any, **kwargs: Any) -> AnalyzerResult:
        """对 store 做一次分析并返回结构化结果。"""


class AnalyzerRegistry:
    """进程内注册表（CLI 可通过名称查找）。"""

    def __init__(self) -> None:
        self._items: Dict[str, Analyzer] = {}

    def register(self, analyzer: Analyzer) -> None:
        if analyzer.name in self._items:
            raise ValueError(f"analyzer already registered: {analyzer.name}")
        self._items[analyzer.name] = analyzer

    def get(self, name: str) -> Analyzer:
        if name not in self._items:
            raise KeyError(f"unknown analyzer: {name}")
        return self._items[name]

    def names(self) -> Iterable[str]:
        return list(self._items.keys())
