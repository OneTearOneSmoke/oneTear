"""EXF 状态机。

设计文档：execution-framework-design.md §8

合法状态：
  PENDING      创建（任务进入 Runner 之前）
  QUEUED       已入队
  DISPATCHED   已派发到 Worker
  RUNNING      正在执行
  SUCCESS      成功
  FAILED       失败（断言 / 命令错误）
  TIMEOUT      超时
  CANCELED     取消
  BLOCKED      依赖失败被跳过
  ERROR        框架内部错误

合法转移（only these）：
  PENDING   -> QUEUED, CANCELED
  QUEUED    -> DISPATCHED, CANCELED
  DISPATCHED-> RUNNING, CANCELED, TIMEOUT
  RUNNING   -> SUCCESS, FAILED, TIMEOUT, CANCELED, ERROR
  *         -> BLOCKED
  终态：SUCCESS, FAILED, TIMEOUT, CANCELED, BLOCKED, ERROR
"""
from __future__ import annotations
from enum import Enum
from typing import Dict, Set, Tuple


class Status(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELED = "CANCELED"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"

    @property
    def is_terminal(self) -> bool:
        return self in TERMINAL


TERMINAL: Set[Status] = {
    Status.SUCCESS, Status.FAILED, Status.TIMEOUT,
    Status.CANCELED, Status.BLOCKED, Status.ERROR,
}

# 终态对应的"成功/失败"语义
PASS_STATUS: Set[Status] = {Status.SUCCESS}
FAIL_STATUS: Set[Status] = {Status.FAILED, Status.TIMEOUT, Status.ERROR}

# 合法转移表
_TRANSITIONS: Dict[Status, Set[Status]] = {
    Status.PENDING:    {Status.QUEUED, Status.CANCELED, Status.BLOCKED, Status.ERROR},
    Status.QUEUED:     {Status.DISPATCHED, Status.CANCELED, Status.BLOCKED, Status.ERROR},
    Status.DISPATCHED: {Status.RUNNING, Status.CANCELED, Status.TIMEOUT, Status.BLOCKED, Status.ERROR},
    Status.RUNNING:    {Status.SUCCESS, Status.FAILED, Status.TIMEOUT, Status.CANCELED, Status.BLOCKED, Status.ERROR},
    # 终态
    Status.SUCCESS:  set(),
    Status.FAILED:   set(),
    Status.TIMEOUT:  set(),
    Status.CANCELED: set(),
    Status.BLOCKED:  set(),
    Status.ERROR:    set(),
}


class IllegalTransition(Exception):
    pass


def can_transition(src: Status, dst: Status) -> bool:
    return dst in _TRANSITIONS.get(src, set())


def transition(src: Status, dst: Status) -> Status:
    if not can_transition(src, dst):
        raise IllegalTransition(f"illegal transition: {src.value} -> {dst.value}")
    return dst


def is_pass(status: Status) -> bool:
    return status in PASS_STATUS


def is_fail(status: Status) -> bool:
    return status in FAIL_STATUS


def is_terminal(status: Status) -> bool:
    return status in TERMINAL


# 终态统一映射到 "ok" 布尔（用于 Result 字段）
def to_ok(status: Status) -> bool:
    return is_pass(status)
