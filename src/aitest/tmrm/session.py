"""Session 生命周期：acquire / release。"""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class SessionStatus(str, Enum):
    ACQUIRED = "acquired"
    RELEASED = "released"
    EXPIRED = "expired"
    FAILED = "failed"


@dataclass
class Session:
    id: str
    machine_id: str
    owner: str                    # 团队 / 用户
    plan_id: Optional[str] = None
    task_id: Optional[str] = None
    acquired_at: float = field(default_factory=time.time)
    released_at: Optional[float] = None
    status: SessionStatus = SessionStatus.ACQUIRED
    ttl_seconds: Optional[float] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def new(
        cls,
        *,
        machine_id: str,
        owner: str,
        plan_id: Optional[str] = None,
        task_id: Optional[str] = None,
        ttl_seconds: Optional[float] = None,
    ) -> "Session":
        return cls(
            id=str(uuid.uuid4()),
            machine_id=machine_id,
            owner=owner,
            plan_id=plan_id,
            task_id=task_id,
            ttl_seconds=ttl_seconds,
        )

    def is_expired(self, now: Optional[float] = None) -> bool:
        if self.ttl_seconds is None or self.released_at is not None:
            return False
        t = now or time.time()
        return (t - self.acquired_at) > self.ttl_seconds
