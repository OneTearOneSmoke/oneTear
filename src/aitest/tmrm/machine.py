"""Machine / Selector 数据类。"""
from __future__ import annotations
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class MachineType(str, Enum):
    HOST = "host"
    BROWSER = "browser"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    SANDBOX = "sandbox"


class MachineStatus(str, Enum):
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"
    UNHEALTHY = "unhealthy"


@dataclass
class Machine:
    id: str
    name: str
    type: MachineType
    spec: Dict[str, Any] = field(default_factory=dict)  # cpu / mem / gpu / disk
    status: MachineStatus = MachineStatus.AVAILABLE
    provider: Optional[str] = None
    region: Optional[str] = None
    zone: Optional[str] = None
    image: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    pool_id: Optional[str] = None
    last_heartbeat: Optional[float] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        d["status"] = self.status.value
        return d


@dataclass
class Selector:
    """机器筛选条件，AND 关系。type / labels / pool 至少一个非空。"""

    type: Optional[MachineType] = None
    labels: Dict[str, str] = field(default_factory=dict)
    pool_id: Optional[str] = None
    provider: Optional[str] = None
    region: Optional[str] = None

    def matches(self, m: Machine) -> bool:
        if self.type is not None and m.type != self.type:
            return False
        if self.pool_id is not None and m.pool_id != self.pool_id:
            return False
        if self.provider is not None and m.provider != self.provider:
            return False
        if self.region is not None and m.region != self.region:
            return False
        for k, v in self.labels.items():
            if m.labels.get(k) != v:
                return False
        return True

    def is_empty(self) -> bool:
        return (
            self.type is None
            and not self.labels
            and self.pool_id is None
            and self.provider is None
            and self.region is None
        )
