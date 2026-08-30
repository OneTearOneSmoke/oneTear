"""EXF 进程级 Worker + 超时/取消/重试（v0.5）。

设计：每个 task 在子进程中执行，父进程通过 multiprocessing.Event 监听取消。
子进程内复用现有 Runner.run_case（in-process 命令/断言），保证向后兼容。

v0.8 之后会替换为：子进程 = sidecar plugin server（gRPC）+ EXF 仅做调度。
本文件保持小而清晰，承载三件事：
  1) 真正并行（多进程）
  2) 硬超时
  3) 取消
  4) 失败分类 + 重试
"""
from __future__ import annotations
import multiprocessing as mp
import os
import signal
import time
import traceback
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .case import Case
from .context import Context
from .errors import CaseFailure, AssertFailure, CommandFailure
from .result import Result
from .state import Status, transition, is_terminal, to_ok


# ---- 重试策略 ----

@dataclass
class RetryPolicy:
    max_attempts: int = 1          # 总尝试次数（含首次）
    backoff: str = "none"          # none | fixed | exponential
    initial_seconds: float = 1.0
    max_seconds: float = 30.0
    retry_on: List[str] = field(default_factory=lambda: ["TIMEOUT", "TRANSIENT"])

    def should_retry(self, status: Status, attempt: int) -> bool:
        if attempt >= self.max_attempts:
            return False
        if status in (Status.SUCCESS, Status.BLOCKED):
            return False
        # 仅对白名单错误重试
        if status == Status.FAILED and "FAILED" not in self.retry_on and "TRANSIENT" not in self.retry_on:
            return False
        return True

    def delay(self, attempt: int) -> float:
        if self.backoff == "none":
            return 0.0
        if self.backoff == "fixed":
            return min(self.initial_seconds, self.max_seconds)
        # exponential
        d = self.initial_seconds * (2 ** (attempt - 1))
        return min(d, self.max_seconds)


# ---- 任务描述 ----

@dataclass
class Task:
    task_id: str
    case: Case
    plan_id: Optional[str] = None
    plugin: Optional[str] = None
    target_id: Optional[str] = None
    timeout_ms: Optional[int] = None
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    labels: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None


# ---- 子进程 worker 函数（必须可 pickle） ----

def _subprocess_run(args: Dict[str, Any]) -> Dict[str, Any]:
    """子进程入口：从 args 重建 Case + Runner，返回 dict 结果。

    args schema：
      {
        "case_dict": {...},        # Case.to_dict()
        "registry_factory": "default",
        "timeout_ms": int,
        "task_id": str,
      }
    """
    from .registry import Registry
    from .runner import Runner

    case_dict = args["case_dict"]
    # 子进程重建最小 Registry（不依赖 CLI 默认组，避免子进程重 import 全部 SDK）
    reg = Registry()
    try:
        # 懒加载：尝试加载 CLI 默认组件，但允许失败（不阻塞子进程）
        from ..cli import _build_default_registry
        reg = _build_default_registry()
    except Exception:  # noqa: BLE001
        # 子进程最少需要这些，否则 case 可能执行不了
        from ..commands.python import PythonEval
        from ..commands.shell import ShellRun
        from ..commands.builtin import MakeTmp, CleanTmp, SeedRng
        from ..assertors.basic import Eq, Ne, Contains, Regex, Truthy
        from ..providers.echo import EchoProvider
        for c in (ShellRun, PythonEval, MakeTmp, CleanTmp, SeedRng):
            reg.command(instance=c())
        for a in (Eq, Ne, Contains, Regex, Truthy):
            reg.assertor(instance=a())
        reg.provider(instance=EchoProvider())
        reg.observer(_SilentObserver())

    case = Case.from_dict(case_dict)
    runner = Runner(reg)

    timeout_ms = args.get("timeout_ms")
    try:
        if timeout_ms:
            import multiprocessing as _mp
            ctx = _mp.get_context("spawn")
            parent_pipe, child_pipe = ctx.Pipe(duplex=False)
            proc = ctx.Process(target=_run_with_pipe, args=(case, runner, child_pipe))
            proc.start()
            proc.join(timeout_ms / 1000.0)
            if proc.is_alive():
                proc.terminate()
                proc.join(1.0)
                if proc.is_alive():
                    proc.kill()
                    proc.join(0.5)
                return _make_error_result(args.get("task_id", ""), case, "TIMEOUT",
                                          f"timeout after {timeout_ms}ms")
            if parent_pipe.poll():
                return parent_pipe.recv()
            return _make_error_result(args.get("task_id", ""), case, "ERROR", "no result from child")
        else:
            return _do_run(case, runner, args.get("task_id", ""))
    except Exception as e:  # noqa: BLE001
        return _make_error_result(args.get("task_id", ""), case, "ERROR",
                                  f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


def _run_with_pipe(case, runner, pipe):
    try:
        out = _do_run(case, runner, getattr(case, "_task_id", ""))
        pipe.send(out)
    except Exception as e:  # noqa: BLE001
        pipe.send(_make_error_result("", case, "ERROR", f"{type(e).__name__}: {e}"))
    finally:
        try:
            pipe.close()
        except Exception:  # noqa: BLE001
            pass


def _do_run(case, runner, task_id: str) -> Dict[str, Any]:
    res = runner.run_case(case)
    return {
        "task_id": task_id,
        "case_id": case.id,
        "case_name": case.name,
        "case_version": None,
        "ok": res.ok,
        "status": res.status,
        "started_at": res.started_at,
        "finished_at": res.finished_at,
        "duration_ms": res.duration_ms,
        "error_code": None,
        "error_message": str(res.error) if res.error else None,
        "error_stack": "".join(traceback.format_exception(type(res.error), res.error, res.error.__traceback__)) if res.error else None,
        "params": dict(getattr(case, "params", {}) or {}),
        "run_output": dict(res.ctx.run) if res.ctx else {},
        "labels": {},
        "artifacts": [],
    }


def _make_error_result(task_id: str, case, status: str, message: str) -> Dict[str, Any]:
    return {
        "task_id": task_id,
        "case_id": case.id if case else "",
        "case_name": case.name if case else "",
        "case_version": None,
        "ok": False,
        "status": status,
        "started_at": time.time(),
        "finished_at": time.time(),
        "duration_ms": 0.0,
        "error_code": status,
        "error_message": message,
        "error_stack": "",
        "params": {},
        "run_output": {},
        "labels": {},
        "artifacts": [],
    }


class _SilentObserver:
    """子进程兜底观察者：丢弃所有事件，避免污染父进程输出。"""
    name = "silent"
    def __getattr__(self, name): return lambda *a, **kw: None


# ---- 调度器（父进程） ----

class WorkerPool:
    """进程级 Worker Pool + 重试 + 超时。

    使用方式：
        pool = WorkerPool(max_workers=4)
        results = pool.run([Task(...), ...])
    """

    def __init__(self, max_workers: int = 4, store: Optional[Any] = None) -> None:
        if max_workers < 1:
            max_workers = 1
        self.max_workers = max_workers
        self.store = store  # 可选 ResultStore

    def run(self, tasks: List[Task], *, on_progress: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        if not tasks:
            return []
        results: List[Dict[str, Any]] = []
        ctx = mp.get_context("spawn")  # spawn 避免 fork 继承复杂状态
        with ProcessPoolExecutor(max_workers=self.max_workers, mp_context=ctx) as ex:
            futs = {}
            for t in tasks:
                self._maybe_store_status(t.task_id, Status.QUEUED, t)
                fut = ex.submit(_subprocess_run, self._task_to_args(t))
                futs[fut] = t

            for fut in as_completed(futs):
                t = futs[fut]
                try:
                    res = fut.result()
                except Exception as e:  # noqa: BLE001
                    res = _make_error_result(t.task_id, t.case, "ERROR", f"{type(e).__name__}: {e}")

                # 重试逻辑
                attempt = 1
                status = Status(res["status"]) if res["status"] in Status.__members__.values() else Status.ERROR
                while t.retry.should_retry(status, attempt):
                    delay = t.retry.delay(attempt)
                    if delay > 0:
                        time.sleep(delay)
                    self._maybe_store_status(t.task_id, Status.RUNNING, t,
                                              error_code="RETRY", error_message=f"retry attempt {attempt + 1}")
                    try:
                        res = _subprocess_run(self._task_to_args(t, attempt=attempt + 1))
                        status = Status(res["status"]) if res["status"] in Status.__members__.values() else Status.ERROR
                    except Exception as e:  # noqa: BLE001
                        res = _make_error_result(t.task_id, t.case, "ERROR", f"{type(e).__name__}: {e}")
                        status = Status.ERROR
                    attempt += 1
                    if attempt >= t.retry.max_attempts:
                        break

                # 终态校验
                if not is_terminal(status):
                    status = Status.ERROR
                    res["status"] = "ERROR"
                    res["ok"] = False
                    res["error_message"] = (res.get("error_message") or "") + " [non-terminal forced to ERROR]"

                res["attempt"] = attempt
                results.append(res)
                if self.store is not None:
                    self._persist(res, t)
                if on_progress is not None:
                    on_progress(res)
        return results

    # ---- 内部 ----
    def _task_to_args(self, t: Task, *, attempt: int = 1) -> Dict[str, Any]:
        return {
            "task_id": t.task_id,
            "case_dict": t.case.to_dict(),
            "timeout_ms": t.timeout_ms,
            "attempt": attempt,
        }

    def _maybe_store_status(self, task_id: str, status: Status, t: Task,
                            *, error_code: str | None = None, error_message: str | None = None) -> None:
        if self.store is None:
            return
        self.store.upsert(
            task_id=task_id, case_id=t.case.id, case_version=None, case_name=t.case.name,
            plan_id=t.plan_id, plugin=t.plugin, target_id=t.target_id,
            status=status.value, attempt=1, trace_id=t.trace_id, labels=t.labels,
        )

    def _persist(self, res: Dict[str, Any], t: Task) -> None:
        if self.store is None:
            return
        self.store.upsert(
            task_id=res["task_id"] or t.task_id,
            case_id=res["case_id"], case_version=res.get("case_version"),
            case_name=res.get("case_name") or t.case.name,
            plan_id=t.plan_id, plugin=t.plugin, target_id=t.target_id,
            status=res["status"],
            attempt=res.get("attempt", 1),
            started_at=res.get("started_at"), finished_at=res.get("finished_at"),
            duration_ms=res.get("duration_ms"),
            error_code=res.get("error_code"),
            error_message=res.get("error_message"),
            error_stack=res.get("error_stack"),
            params=res.get("params"),
            run_output=res.get("run_output"),
            labels=t.labels,
            artifacts=res.get("artifacts"),
            trace_id=t.trace_id,
        )
