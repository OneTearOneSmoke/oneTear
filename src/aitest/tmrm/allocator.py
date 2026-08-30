"""分配器：acquire / release + 配额。"""
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import List, Optional

from .machine import Machine, MachineStatus, Selector
from .session import Session, SessionStatus
from .store import FarmStore
from .quota import QuotaPolicy


class AllocationError(RuntimeError):
    pass


class QuotaExceeded(AllocationError):
    pass


class NoMatch(AllocationError):
    pass


@dataclass
class AllocateRequest:
    owner: str
    selector: Selector
    plan_id: Optional[str] = None
    task_id: Optional[str] = None
    ttl_seconds: Optional[float] = None


class Allocator:
    def __init__(self, store: FarmStore, quota: Optional[QuotaPolicy] = None) -> None:
        self.store = store
        self.quota = quota or QuotaPolicy()

    def acquire(self, req: AllocateRequest) -> Session:
        if req.selector.is_empty():
            raise AllocationError("selector must not be empty")
        # 配额：按 (team, pool_id) 检查；若 selector 没指定 pool_id，则跳过配额
        if req.selector.pool_id is not None:
            current = len(self.store.list_sessions(owner=req.owner, status=SessionStatus.ACQUIRED))
            if not self.quota.check_concurrent(req.owner, req.selector.pool_id, current):
                raise QuotaExceeded(
                    f"quota exceeded for team={req.owner} pool={req.selector.pool_id}"
                )

        # 选机器
        candidates = self.store.list_machines(
            status=MachineStatus.AVAILABLE,
            machine_type=req.selector.type,
            pool_id=req.selector.pool_id,
            limit=10000,
        )
        match: Optional[Machine] = None
        for m in candidates:
            if req.selector.matches(m):
                match = m
                break
        if match is None:
            raise NoMatch(f"no machine matches selector {req.selector}")

        # 标记机器 allocated + 写 session
        match.status = MachineStatus.ALLOCATED
        self.store.upsert_machine(match)

        sess = Session.new(
            machine_id=match.id, owner=req.owner,
            plan_id=req.plan_id, task_id=req.task_id,
            ttl_seconds=req.ttl_seconds,
        )
        self.store.insert_session(sess)
        return sess

    def release(self, session_id: str) -> Session:
        sess = self.store.get_session(session_id)
        if sess is None:
            raise AllocationError(f"unknown session: {session_id}")
        if sess.status != SessionStatus.ACQUIRED:
            raise AllocationError(f"session {session_id} not active (status={sess.status})")
        # 释放机器
        m = self.store.get_machine(sess.machine_id)
        if m is not None:
            m.status = MachineStatus.AVAILABLE
            self.store.upsert_machine(m)
        # 释放 session
        sess.released_at = time.time()
        sess.status = SessionStatus.RELEASED
        self.store.update_session(sess)
        return sess
