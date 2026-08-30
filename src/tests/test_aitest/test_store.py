import time
import pytest

from aitest.core.state import Status
from aitest.core.store import ResultStore


@pytest.fixture
def store(tmp_path):
    s = ResultStore(str(tmp_path / "results.db"))
    yield s
    s.close()


def _row(**kw):
    base = dict(
        task_id="t1", case_id="c1", status=Status.RUNNING.value,
        case_name="c1", case_version=1, plan_id="p1",
        plugin="shell.run", target_id="tgt-1",
        attempt=1, started_at=time.time(), finished_at=None,
        duration_ms=None,
    )
    base.update(kw)
    return base


def test_upsert_and_get(store):
    store.upsert(**_row())
    row = store.get("t1")
    assert row is not None
    assert row.case_id == "c1"
    assert row.status == "RUNNING"
    assert row.attempt == 1


def test_upsert_overwrites_by_task_id(store):
    store.upsert(**_row(status="QUEUED"))
    store.upsert(**_row(status="RUNNING"))
    store.upsert(**_row(status="SUCCESS", finished_at=time.time(), duration_ms=12.3))
    row = store.get("t1")
    assert row.status == "SUCCESS"
    assert row.duration_ms == pytest.approx(12.3)


def test_mark_status(store):
    store.upsert(**_row(status="RUNNING"))
    store.mark_status("t1", "FAILED", error_code="ASSERT_FAIL",
                      error_message="value != expect")
    row = store.get("t1")
    assert row.status == "FAILED"
    assert row.error_code == "ASSERT_FAIL"


def test_list_by_case(store):
    for i in range(3):
        store.upsert(task_id=f"t{i}", case_id="c1", status="SUCCESS",
                     case_name="c1", case_version=1, plan_id="p1",
                     plugin="x", target_id="tgt",
                     started_at=time.time() - i, finished_at=time.time(),
                     duration_ms=1.0)
    store.upsert(task_id="t9", case_id="c2", status="FAILED",
                 case_name="c2", case_version=1, plan_id="p1",
                 plugin="x", target_id="tgt",
                 started_at=time.time(), finished_at=time.time(),
                 duration_ms=1.0, error_code="X")
    rows = store.list_by_case("c1", limit=10)
    assert len(rows) == 3
    assert all(r.case_id == "c1" for r in rows)


def test_list_by_plan(store):
    for i in range(2):
        store.upsert(task_id=f"t{i}", case_id="c1", status="SUCCESS",
                     case_name="c1", case_version=1, plan_id="p1",
                     plugin="x", target_id="tgt",
                     started_at=time.time(), finished_at=time.time(), duration_ms=1.0)
    store.upsert(task_id="t9", case_id="c2", status="FAILED",
                 case_name="c2", case_version=1, plan_id="p2",
                 plugin="x", target_id="tgt",
                 started_at=time.time(), finished_at=time.time(), duration_ms=1.0, error_code="X")
    p1_rows = store.list_by_plan("p1")
    assert len(p1_rows) == 2
    assert all(r.plan_id == "p1" for r in p1_rows)


def test_summary(store):
    for i in range(3):
        store.upsert(task_id=f"s{i}", case_id="c1", status="SUCCESS",
                     case_name="c1", case_version=1, plan_id="p1",
                     plugin="x", target_id="tgt",
                     started_at=time.time(), finished_at=time.time(), duration_ms=1.0)
    for i in range(2):
        store.upsert(task_id=f"f{i}", case_id="c1", status="FAILED",
                     case_name="c1", case_version=1, plan_id="p1",
                     plugin="x", target_id="tgt",
                     started_at=time.time(), finished_at=time.time(),
                     duration_ms=1.0, error_code="X")
    s = store.summary()
    assert s.get("SUCCESS") == 3
    assert s.get("FAILED") == 2


def test_recent_ordering(store):
    for i in range(3):
        store.upsert(task_id=f"r{i}", case_id="c1", status="SUCCESS",
                     case_name="c1", case_version=1, plan_id="p1",
                     plugin="x", target_id="tgt",
                     started_at=time.time() + i, finished_at=time.time(), duration_ms=1.0)
    rows = store.recent(limit=2)
    assert len(rows) == 2
