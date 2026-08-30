"""TMRM (Test Machine Resource Management) / Test Farm 子系统原型。

按 [`test-machine-resource-management-design.md`](../docs/ai-test/test-machine-resource-management-design.md)：

  - 管理 ≥ 10K 机器 / 设备（host / browser / mobile / desktop / sandbox）
  - 分配 P95 ≤ 200 ms；释放同步，回收异步
  - 健康检查 30 s 一次；故障机器 60 s 内摘除
  - 多云 + 私有 IDC（v1.0 落地）
  - 配额、计费、维护计划（v1.0）

v0.5 δ Python 原型：先做 5 个核心对象 + 分配器 + SQLite 持久化 + 健康心跳；
gRPC / K8s 适配留到 v0.8。

模块边界：
  - machine : Machine / Pool / Selector dataclass
  - session : Session 生命周期
  - store   : SQLite 注册表
  - allocator: acquire / release + 配额检查
  - health  : 心跳 + 健康打分
  - quota   : 配额策略（按 team / pool / 时间窗）

对外 API 全部 dataclass，便于 Rust / Go 端 1:1 翻译。
"""

from .machine import Machine, MachineStatus, MachineType, Selector
from .pool import Pool
from .session import Session, SessionStatus
from .store import FarmStore
from .allocator import Allocator, AllocationError, QuotaExceeded
from .health import HealthChecker, HealthRecord, HealthStatus
from .quota import Quota, QuotaPolicy

__all__ = [
    "Machine", "MachineStatus", "MachineType", "Selector",
    "Pool",
    "Session", "SessionStatus",
    "FarmStore",
    "Allocator", "AllocationError", "QuotaExceeded",
    "HealthChecker", "HealthRecord", "HealthStatus",
    "Quota", "QuotaPolicy",
]
