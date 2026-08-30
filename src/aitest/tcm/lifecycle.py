"""Case Lifecycle —— 用例生命周期状态机 + 转移规则。

按 [`test-case-management-design.md`](../docs/ai-test/test-case-management-design.md) §生命周期：

    draft ──new──> active ──mark_deprecated──> deprecated ──retire──> retired
                        │                            │
                        └───un_deprecate────────────┘

合法转移 + 非法转移一律抛 `IllegalTransition`，与 EXF 状态机对齐。

模块边界：只关心"用例作为资产管理"的元数据层，不掺 EXF 执行结果。
"""
from __future__ import annotations
from enum import Enum
from typing import Dict, Iterable, List, Set


class LifecycleStatus(str, Enum):
    """用例生命周期状态。"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class IllegalTransition(ValueError):
    """非法的状态转移。"""


# 合法转移表（from → set(to)）
_TRANSITIONS: Dict[LifecycleStatus, Set[LifecycleStatus]] = {
    LifecycleStatus.DRAFT: {LifecycleStatus.ACTIVE, LifecycleStatus.RETIRED},
    LifecycleStatus.ACTIVE: {LifecycleStatus.DEPRECATED, LifecycleStatus.RETIRED},
    LifecycleStatus.DEPRECATED: {LifecycleStatus.ACTIVE, LifecycleStatus.RETIRED},
    LifecycleStatus.RETIRED: set(),  # terminal
}


def allowed_next(status: LifecycleStatus) -> List[LifecycleStatus]:
    return sorted(_TRANSITIONS.get(status, set()), key=lambda s: s.value)


def transition(from_status: LifecycleStatus, to_status: LifecycleStatus) -> LifecycleStatus:
    """校验状态机转移；合法返回 to_status，非法抛 IllegalTransition。"""
    if from_status == to_status:
        return to_status
    if to_status not in _TRANSITIONS.get(from_status, set()):
        raise IllegalTransition(
            f"illegal lifecycle transition: {from_status.value} → {to_status.value}"
        )
    return to_status


def is_terminal(status: LifecycleStatus) -> bool:
    return status == LifecycleStatus.RETIRED


def can_run(status: LifecycleStatus) -> bool:
    """只有 ACTIVE / DEPRECATED 可以被 EXF 执行。"""
    return status in (LifecycleStatus.ACTIVE, LifecycleStatus.DEPRECATED)
