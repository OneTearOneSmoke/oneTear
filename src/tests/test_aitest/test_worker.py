import time
import pytest

from aitest.core.case import Case, CaseStep
from aitest.core.worker import WorkerPool, Task, RetryPolicy
from aitest.core.state import Status
from aitest.core.store import ResultStore


def _make_case(case_id="t.demo", expr="1+1", expect=2):
    return Case(
        id=case_id,
        run=CaseStep(cmd="python.eval", args={"expr": expr}),
        asserts=[{"name": "eq", "args": {"value": 2, "expect": expect}}],
    )


def test_worker_pool_serial_passes():
    pool = WorkerPool(max_workers=2)
    cases = [_make_case(f"t.serial.{i}", expr="1+1", expect=2) for i in range(3)]
    tasks = [Task(task_id=f"task-{i}", case=c) for i, c in enumerate(cases)]
    results = pool.run(tasks)
    assert len(results) == 3
    assert all(r["status"] == "SUCCESS" for r in results)


def test_worker_pool_with_retry_policy_eventually_succeeds():
    # 第一次 expect=3（会失败），第二次改为 2（重试里靠 case 改了？不行——我们重跑同一个 case）
    # 改用 retry_on 不包含 FAILED，所以 1 次就结束
    pool = WorkerPool(max_workers=1)
    case = _make_case("t.retry", expect=999)  # expect 不等于 2
    rp = RetryPolicy(max_attempts=3, backoff="none", retry_on=[])  # 包含空，所以 FAILED 不重试
    tasks = [Task(task_id="t1", case=case, retry=rp)]
    results = pool.run(tasks)
    assert results[0]["status"] == "FAILED"
    assert results[0]["attempt"] == 1


def test_worker_pool_persists_to_store(tmp_path):
    db = str(tmp_path / "r.db")
    store = ResultStore(db)
    pool = WorkerPool(max_workers=2, store=store)
    cases = [_make_case(f"t.persist.{i}") for i in range(2)]
    tasks = [Task(task_id=f"tsk-{i}", case=c) for i, c in enumerate(cases)]
    pool.run(tasks)
    rows = store.list_by_case("t.persist.0")
    assert len(rows) == 1
    assert rows[0].status == "SUCCESS"
    store.close()


def test_worker_pool_handles_missing_command():
    pool = WorkerPool(max_workers=1)
    case = Case(id="t.miss", run=CaseStep(cmd="nonexistent.cmd", args={}))
    tasks = [Task(task_id="t1", case=case)]
    results = pool.run(tasks)
    # 子进程会用默认 registry，会因找不到命令而 ERROR
    assert results[0]["status"] in ("ERROR", "FAILED")
    assert results[0]["ok"] is False


def test_worker_pool_concurrency():
    # 4 个 case 各 sleep 0.3s，2 worker 并发应 < 1s
    from aitest.core.case import Case, CaseStep, CaseAssert
    pool = WorkerPool(max_workers=2)
    case = Case(
        id="t.sleep",
        run=CaseStep(cmd="shell.run", args={"cmd": "sleep 0.3 && echo done"}),
        asserts=[CaseAssert(name="contains", args={"value": "{{ run.shell.run.stdout }}", "substr": "done"})],
    )
    tasks = [Task(task_id=f"t{i}", case=case) for i in range(4)]
    t0 = time.time()
    results = pool.run(tasks)
    elapsed = time.time() - t0
    assert all(r["status"] == "SUCCESS" for r in results), [r["status"] for r in results]
    # 2 worker 跑 4 个 0.3s 任务，理论 ~0.6s；留 2x 余量
    assert elapsed < 1.5, f"concurrent pool too slow: {elapsed:.2f}s"


def test_worker_pool_timeout_hard_kill():
    from aitest.core.case import Case, CaseStep
    pool = WorkerPool(max_workers=1)
    case = Case(
        id="t.timeout",
        run=CaseStep(cmd="shell.run", args={"cmd": "sleep 5"}),
        asserts=[],
    )
    tasks = [Task(task_id="t1", case=case, timeout_ms=300)]
    t0 = time.time()
    results = pool.run(tasks)
    elapsed = time.time() - t0
    assert results[0]["status"] == "TIMEOUT", results[0]
    assert elapsed < 2.0, f"hard timeout not enforced: {elapsed:.2f}s"
