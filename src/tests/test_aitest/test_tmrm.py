"""TMRM (Test Machine Resource Management) 单测。"""
from __future__ import annotations
import os
import tempfile
import time
from typing import List

import pytest

from aitest.tmrm.machine import Machine, MachineStatus, MachineType, Selector
from aitest.tmrm.pool import Pool
from aitest.tmrm.session import Session, SessionStatus
from aitest.tmrm.store import FarmStore
from aitest.tmrm.allocator import Allocator, AllocateRequest, AllocationError, QuotaExceeded, NoMatch
from aitest.tmrm.quota import Quota, QuotaPolicy
from aitest.tmrm.health import HealthChecker, HealthStatus


# ──────────── Fixtures ────────────

@pytest.fixture
def store_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


@pytest.fixture
def store(store_path):
    s = FarmStore(store_path)
    yield s
    s.close()


def _mk_machine(mid: str, *, mtype=MachineType.HOST, status=MachineStatus.AVAILABLE,
                pool_id=None, labels=None, provider=None, region=None,
                heartbeat: float | None = None) -> Machine:
    m = Machine(
        id=mid, name=f"m-{mid}", type=mtype, status=status,
        pool_id=pool_id, labels=labels or {}, provider=provider, region=region,
    )
    m.last_heartbeat = heartbeat
    return m


# ──────────── Machine / Selector ────────────

class TestMachineSelector:
    def test_selector_by_type(self):
        s = Selector(type=MachineType.BROWSER)
        assert s.matches(_mk_machine("m1", mtype=MachineType.BROWSER))
        assert not s.matches(_mk_machine("m2", mtype=MachineType.HOST))

    def test_selector_by_labels_and(self):
        s = Selector(labels={"os": "linux", "tier": "fast"})
        assert s.matches(_mk_machine("m1", labels={"os": "linux", "tier": "fast", "x": "1"}))
        assert not s.matches(_mk_machine("m2", labels={"os": "linux"}))

    def test_selector_by_pool_and_region(self):
        s = Selector(pool_id="p1", region="us-west-2")
        assert s.matches(_mk_machine("m1", pool_id="p1", region="us-west-2"))
        assert not s.matches(_mk_machine("m2", pool_id="p2", region="us-west-2"))

    def test_empty_selector_is_empty(self):
        assert Selector().is_empty()
        assert not Selector(type=MachineType.HOST).is_empty()


# ──────────── Session ────────────

class TestSession:
    def test_new_session_defaults(self):
        s = Session.new(machine_id="m1", owner="teamA")
        assert s.machine_id == "m1"
        assert s.owner == "teamA"
        assert s.status == SessionStatus.ACQUIRED
        assert s.released_at is None
        assert s.acquired_at > 0

    def test_is_expired(self):
        s = Session.new(machine_id="m1", owner="o", ttl_seconds=10)
        s.acquired_at = time.time() - 100
        assert s.is_expired() is True


# ──────────── Store ────────────

class TestFarmStore:
    def test_machine_roundtrip(self, store):
        m = _mk_machine("m1", labels={"env": "ci"})
        store.upsert_machine(m)
        m2 = store.get_machine("m1")
        assert m2 is not None
        assert m2.labels == {"env": "ci"}

    def test_list_by_status(self, store):
        store.upsert_machine(_mk_machine("m1", status=MachineStatus.AVAILABLE))
        store.upsert_machine(_mk_machine("m2", status=MachineStatus.MAINTENANCE))
        rows = store.list_machines(status=MachineStatus.AVAILABLE)
        assert {r.id for r in rows} == {"m1"}

    def test_pool_roundtrip(self, store):
        from aitest.tmrm.machine import Selector
        p = Pool(id="p1", name="pool1", selectors=Selector(type=MachineType.HOST, pool_id="p1"))
        store.upsert_pool(p)
        pools = store.list_pools()
        assert len(pools) == 1
        assert pools[0].selectors.type == MachineType.HOST

    def test_session_roundtrip(self, store):
        s = Session.new(machine_id="m1", owner="o")
        store.insert_session(s)
        s2 = store.get_session(s.id)
        assert s2 is not None
        assert s2.machine_id == "m1"
        assert s2.status == SessionStatus.ACQUIRED


# ──────────── Allocator ────────────

class TestAllocator:
    def test_acquire_then_release(self, store):
        store.upsert_machine(_mk_machine("m1"))
        a = Allocator(store)
        sess = a.acquire(AllocateRequest(owner="teamA", selector=Selector(type=MachineType.HOST)))
        assert sess.machine_id == "m1"
        # 机器已变 ALLOCATED
        assert store.get_machine("m1").status == MachineStatus.ALLOCATED
        a.release(sess.id)
        # 机器回到 AVAILABLE
        assert store.get_machine("m1").status == MachineStatus.AVAILABLE
        # session 状态
        assert store.get_session(sess.id).status == SessionStatus.RELEASED

    def test_acquire_picks_matching_machine(self, store):
        store.upsert_machine(_mk_machine("m1", labels={"env": "staging"}))
        store.upsert_machine(_mk_machine("m2", labels={"env": "prod"}))
        a = Allocator(store)
        sess = a.acquire(
            AllocateRequest(
                owner="teamA",
                selector=Selector(type=MachineType.HOST, labels={"env": "prod"}),
            )
        )
        assert sess.machine_id == "m2"

    def test_acquire_no_match_raises(self, store):
        store.upsert_machine(_mk_machine("m1", mtype=MachineType.BROWSER))
        a = Allocator(store)
        with pytest.raises(NoMatch):
            a.acquire(AllocateRequest(owner="o", selector=Selector(type=MachineType.MOBILE)))

    def test_acquire_quota_enforced(self, store):
        store.upsert_machine(_mk_machine("m1", pool_id="p1"))
        store.upsert_machine(_mk_machine("m2", pool_id="p1"))
        qp = QuotaPolicy()
        qp.set(Quota(team_id="teamA", pool_id="p1", max_concurrent=1))
        a = Allocator(store, quota=qp)
        a.acquire(AllocateRequest(owner="teamA", selector=Selector(pool_id="p1")))
        with pytest.raises(QuotaExceeded):
            a.acquire(AllocateRequest(owner="teamA", selector=Selector(pool_id="p1")))

    def test_acquire_rejects_empty_selector(self, store):
        a = Allocator(store)
        with pytest.raises(AllocationError):
            a.acquire(AllocateRequest(owner="o", selector=Selector()))


# ──────────── Health ────────────

class TestHealthChecker:
    def test_heartbeat_updates_field(self, store):
        store.upsert_machine(_mk_machine("m1"))
        hc = HealthChecker(store)
        m = hc.heartbeat("m1")
        assert m.last_heartbeat is not None
        assert m.last_heartbeat > 0

    def test_check_ok_when_fresh(self, store):
        m = _mk_machine("m1", heartbeat=time.time())
        store.upsert_machine(m)
        hc = HealthChecker(store)
        rec = hc.check_one("m1")
        assert rec.status == HealthStatus.OK
        assert rec.error == ""

    def test_check_unhealthy_when_stale(self, store):
        m = _mk_machine("m1", heartbeat=time.time() - 1000)  # 1000s ago
        store.upsert_machine(m)
        hc = HealthChecker(store)
        rec = hc.check_one("m1")
        assert rec.status == HealthStatus.UNHEALTHY
        assert "stale" in rec.error
        # 机器状态变成 UNHEALTHY
        m2 = store.get_machine("m1")
        assert m2.status == MachineStatus.UNHEALTHY

    def test_sweep_returns_list(self, store):
        store.upsert_machine(_mk_machine("m1", heartbeat=time.time()))
        store.upsert_machine(_mk_machine("m2", heartbeat=time.time() - 1000))
        hc = HealthChecker(store)
        recs = hc.sweep()
        assert len(recs) == 2
        statuses = {r.machine_id: r.status for r in recs}
        assert statuses["m1"] == HealthStatus.OK
        assert statuses["m2"] == HealthStatus.UNHEALTHY
