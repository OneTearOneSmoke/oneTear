"""Examples: 演示 EXF v0.5 内核（状态机 / SQLite Store / 进程 Worker / 重试 / 超时）。

跑法：
    cd src && python3 -m examples.run_with_worker_pool
"""
from __future__ import annotations
import os
import time
import tempfile

from aitest.core.case import Case, CaseStep, CaseAssert
from aitest.core.worker import WorkerPool, Task, RetryPolicy
from aitest.core.store import ResultStore
from aitest.core.state import Status


def make_case(case_id: str, sleep: float = 0.0, expr: str = "1+1") -> Case:
    """构造一个 shell.run 跑 expr 的 case。"""
    cmd = f"sleep {sleep} && echo {expr}" if sleep else f"echo {expr}"
    return Case(
        id=case_id,
        name=f"demo {case_id}",
        tags=["demo"],
        run=CaseStep(cmd="shell.run", args={"cmd": cmd}),
        asserts=[
            CaseAssert(
                name="contains",
                args={"value": "{{ run.shell.run.stdout }}", "substr": expr},
            )
        ],
    )


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="aitest-demo-")
    db = os.path.join(tmp, "results.db")
    print(f"[demo] using store: {db}")

    store = ResultStore(db)
    pool = WorkerPool(max_workers=4, store=store)

    # 1) 串行：3 个简单 case
    print("\n=== 1) serial 3 simple cases ===")
    cases = [make_case(f"demo.simple.{i}", sleep=0.05) for i in range(3)]
    tasks = [Task(task_id=f"t.simple.{i}", case=c) for i, c in enumerate(cases)]
    t0 = time.time()
    results = pool.run(tasks)
    print(f"  -> {len(results)} results in {(time.time()-t0)*1000:.1f} ms")
    for r in results:
        print(f"  - {r['case_id']:<22} status={r['status']:<8} dur={r['duration_ms']:.2f} ms")

    # 2) 并发：6 个 sleep 0.3s 的 case，4 worker
    print("\n=== 2) concurrent 6x sleep(0.3) on 4 workers ===")
    cases = [make_case(f"demo.sleep.{i}", sleep=0.3) for i in range(6)]
    tasks = [Task(task_id=f"t.sleep.{i}", case=c) for i, c in enumerate(cases)]
    t0 = time.time()
    results = pool.run(tasks)
    elapsed = time.time() - t0
    print(f"  -> {len(results)} results in {elapsed*1000:.1f} ms "
          f"(serial would be ~1800ms, expect ~600ms with 4 workers)")
    assert elapsed < 1.2, f"concurrent not working: {elapsed:.2f}s"

    # 3) 超时硬杀
    print("\n=== 3) hard timeout 200ms on a 2s case ===")
    slow = make_case("demo.timeout", sleep=2.0)
    tasks = [Task(task_id="t.timeout", case=slow, timeout_ms=200)]
    t0 = time.time()
    results = pool.run(tasks)
    elapsed = time.time() - t0
    print(f"  -> status={results[0]['status']:<8} elapsed={elapsed*1000:.0f}ms")
    assert results[0]["status"] == Status.TIMEOUT.value, results[0]

    # 4) 重试（带退避）
    print("\n=== 4) retry 3x with exponential backoff on a failing case ===")
    fail = Case(
        id="demo.retry",
        name="always fails",
        run=CaseStep(cmd="shell.run", args={"cmd": "echo nope"}),
        asserts=[
            CaseAssert(name="contains",
                       args={"value": "{{ run.shell.run.stdout }}", "substr": "yes"})
        ],
    )
    rp = RetryPolicy(max_attempts=3, backoff="fixed", initial_seconds=0.1,
                     retry_on=["FAILED"])
    tasks = [Task(task_id="t.retry", case=fail, retry=rp)]
    t0 = time.time()
    results = pool.run(tasks)
    elapsed = time.time() - t0
    print(f"  -> status={results[0]['status']:<8} attempt={results[0]['attempt']} "
          f"elapsed={elapsed*1000:.0f}ms")
    assert results[0]["status"] == Status.FAILED.value
    assert results[0]["attempt"] == 3

    # 5) Result-Store 查询
    print("\n=== 5) query Result-Store ===")
    print(f"  summary: {store.summary()}")
    rows = store.recent(limit=20)
    print(f"  recent: {len(rows)} rows")
    fails = store.list_by_status(Status.FAILED.value, limit=5)
    print(f"  failed rows: {len(fails)}")
    for r in fails[:3]:
        print(f"    - {r.case_id:<22} dur={r.duration_ms:.1f}ms err={r.error_code}")

    store.close()
    print("\n[done] all examples passed")


if __name__ == "__main__":
    main()
