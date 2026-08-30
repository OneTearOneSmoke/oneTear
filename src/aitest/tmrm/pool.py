"""Pool 资源池。"""
from __future__ import annotations
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

from .machine import Selector


@dataclass
class Pool:
    """机器池。selectors 用于自动注册时的过滤。"""

    id: str
    name: str
    selectors: Selector = field(default_factory=Selector)
    description: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["selectors"] = {
            "type": self.selectors.type.value if self.selectors.type else None,
            "labels": self.selectors.labels,
            "pool_id": self.selectors.pool_id,
            "provider": self.selectors.provider,
            "region": self.selectors.region,
        }
        return d
