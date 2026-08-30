"""Quota 配额策略。"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Quota:
    """单条配额：team_id / pool_id 维度下，同时在跑的 session 上限。"""
    team_id: str
    pool_id: str
    max_concurrent: int = 10
    max_daily: int = 1000


@dataclass
class QuotaPolicy:
    """内存级配额表（v0.5 δ；v1.0 切到 Redis counter）。"""
    _quotas: Dict[str, Quota] = field(default_factory=dict)

    def _key(self, team_id: str, pool_id: str) -> str:
        return f"{team_id}::{pool_id}"

    def set(self, q: Quota) -> None:
        self._quotas[self._key(q.team_id, q.pool_id)] = q

    def get(self, team_id: str, pool_id: str) -> Optional[Quota]:
        return self._quotas.get(self._key(team_id, pool_id))

    def check_concurrent(self, team_id: str, pool_id: str, current: int) -> bool:
        q = self.get(team_id, pool_id)
        if q is None:
            return True  # 未配置 = 不限
        return current < q.max_concurrent
