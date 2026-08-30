"""健康检查 + 心跳。"""
from __future__ import annotations
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from .machine import Machine, MachineStatus
from .store import FarmStore


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthRecord:
    machine_id: str
    at: float
    status: HealthStatus
    latency_ms: int
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "machine_id": self.machine_id,
            "at": self.at,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


# Probe 协议：返回 (latency_ms, error_str)，error 为 "" 表示 OK
Probe = Callable[[Machine], tuple]


def default_probe(m: Machine) -> tuple:
    """原型：默认探针 = 根据 last_heartbeat 推算。

    真实场景应换成 ssh ping / http probe / docker inspect。
    """
    if m.last_heartbeat is None:
        return (0, "no heartbeat recorded")
    age = time.time() - m.last_heartbeat
    if age > 300:
        return (int(age * 1000), f"heartbeat stale ({age:.0f}s)")
    return (int(age * 1000), "")


class HealthChecker:
    def __init__(self, store: FarmStore, probe: Optional[Probe] = None,
                 *, stale_seconds: float = 60.0) -> None:
        self.store = store
        self.probe = probe or default_probe
        self.stale_seconds = stale_seconds

    def heartbeat(self, machine_id: str) -> Machine:
        m = self.store.get_machine(machine_id)
        if m is None:
            raise KeyError(f"unknown machine: {machine_id}")
        m.last_heartbeat = time.time()
        self.store.upsert_machine(m)
        return m

    def check_one(self, machine_id: str) -> HealthRecord:
        m = self.store.get_machine(machine_id)
        if m is None:
            raise KeyError(f"unknown machine: {machine_id}")
        latency_ms, err = self.probe(m)
        if err:
            status = HealthStatus.UNHEALTHY if "stale" in err else HealthStatus.DEGRADED
        else:
            status = HealthStatus.OK
        rec = HealthRecord(
            machine_id=m.id, at=time.time(),
            status=status, latency_ms=latency_ms, error=err,
        )
        self.store.append_health(m.id, status.value, latency_ms, err)
        # 标记 unhealthy
        if status == HealthStatus.UNHEALTHY:
            m.status = MachineStatus.UNHEALTHY
            self.store.upsert_machine(m)
        return rec

    def sweep(self) -> list:
        """扫描所有非 RETIRED 的机器，更新状态。"""
        out = []
        for m in self.store.list_machines(limit=100000):
            if m.status == MachineStatus.RETIRED:
                continue
            out.append(self.check_one(m.id))
        return out
