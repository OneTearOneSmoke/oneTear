"""TRM (Test Report Management) 子系统原型。

职责：
  - 消费 EXF 写入的 Result-Store，做高阶分析（flaky / baseline / trend / summary）
  - 暴露 CLI 子命令 `aitest report`
  - 提供可扩展的 Analyzer 协议，方便 v1.0 接入 ClickHouse / Postgres

不重复 EXF 已经做的工作（执行、调度、状态机），只做"读 + 分析"。

模块边界：
  - store    : 轻包装 EXF ResultStore，补 TRM 关心的查询
  - flaky    : Flaky 检测（滑动窗口 + 失败比例）
  - baseline : 基线对比（两 run 之间的 diff）
  - trend    : 趋势/健康指标（按 case 的状态时间线 + 通过率）
  - analyzer : 抽象协议，方便 v0.8 之后接入更多分析器

对外 API 全部以 dataclass 返回（dict-of-rows），与 EXF 的 ResultRow 解耦。
"""

from .flaky import FlakyDetector, FlakyCase
from .baseline import BaselineComparator, BaselineDiff
from .trend import TrendAnalyzer, CaseTrend
from .analyzer import Analyzer, AnalyzerRegistry

__all__ = [
    "FlakyDetector",
    "FlakyCase",
    "BaselineComparator",
    "BaselineDiff",
    "TrendAnalyzer",
    "CaseTrend",
    "Analyzer",
    "AnalyzerRegistry",
]
