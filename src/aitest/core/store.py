"""SQLite Result-Store（v0.5）。

职责：
  - 持久化每次执行结果（result / status / 时序 / 错误 / artifacts）
  - 按 case / plan / status / 时间 查询
  - 提供 replay 入口（按 task_id 取历史）

Schema：
  task_results  任务结果（主表）
  case_runs     按 case 聚合的最新/历史快照（用于查询加速）
"""
from __future__ import annotations
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .state import Status


SCHEMA = """
CREATE TABLE IF NOT EXISTS task_results (
  task_id       TEXT PRIMARY KEY,
  case_id       TEXT NOT NULL,
  case_version  INTEGER,
  case_name     TEXT,
  plan_id       TEXT,
  plugin        TEXT,
  target_id     TEXT,
  status        TEXT NOT NULL,
  attempt       INTEGER NOT NULL DEFAULT 1,
  started_at    REAL,
  finished_at   REAL,
  duration_ms   REAL,
  error_code    TEXT,
  error_message TEXT,
  error_stack   TEXT,
  params        TEXT,
  run_output    TEXT,
  labels        TEXT,
  artifacts     TEXT,
  trace_id      TEXT,
  created_at    REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_task_case   ON task_results(case_id);
CREATE INDEX IF NOT EXISTS idx_task_plan   ON task_results(plan_id);
CREATE INDEX IF NOT EXISTS idx_task_status ON task_results(status);
CREATE INDEX IF NOT EXISTS idx_task_time   ON task_results(started_at);

CREATE TABLE IF NOT EXISTS runs (
  run_id     TEXT PRIMARY KEY,
  plan_id    TEXT,
  started_at REAL NOT NULL,
  finished_at REAL,
  total      INTEGER NOT NULL DEFAULT 0,
  passed     INTEGER NOT NULL DEFAULT 0,
  failed     INTEGER NOT NULL DEFAULT 0,
  meta       TEXT
);
"""


@dataclass
class ResultRow:
    task_id: str
    case_id: str
    case_version: Optional[int]
    case_name: str
    plan_id: Optional[str]
    plugin: Optional[str]
    target_id: Optional[str]
    status: str
    attempt: int
    started_at: Optional[float]
    finished_at: Optional[float]
    duration_ms: Optional[float]
    error_code: Optional[str]
    error_message: Optional[str]
    error_stack: Optional[str]
    params: Dict[str, Any]
    run_output: Dict[str, Any]
    labels: Dict[str, Any]
    artifacts: List[Dict[str, Any]]
    trace_id: Optional[str]
    created_at: float

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "case_id": self.case_id,
            "case_version": self.case_version,
            "case_name": self.case_name,
            "plan_id": self.plan_id,
            "plugin": self.plugin,
            "target_id": self.target_id,
            "status": self.status,
            "attempt": self.attempt,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "error_stack": self.error_stack,
            "params": self.params,
            "run_output": self.run_output,
            "labels": self.labels,
            "artifacts": self.artifacts,
            "trace_id": self.trace_id,
            "created_at": self.created_at,
        }


def _connect(path: str) -> sqlite3.Connection:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _json(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, ensure_ascii=False, default=str)
    return str(obj)


def _loads(s: Optional[str]) -> Any:
    if not s:
        return {} if s is None or s == "" else None
    try:
        return json.loads(s)
    except Exception:  # noqa: BLE001
        return s


class ResultStore:
    """SQLite 持久化 Result-Store。线程/进程安全由 SQLite 自身保证。"""

    def __init__(self, path: str = "aitest-results.db") -> None:
        self.path = path
        self._conn = _connect(path)

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # noqa: BLE001
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---- 写 ----
    def upsert(
        self,
        *,
        task_id: str,
        case_id: str,
        status: str,
        case_version: Optional[int] = None,
        case_name: str = "",
        plan_id: Optional[str] = None,
        plugin: Optional[str] = None,
        target_id: Optional[str] = None,
        attempt: int = 1,
        started_at: Optional[float] = None,
        finished_at: Optional[float] = None,
        duration_ms: Optional[float] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        error_stack: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        run_output: Optional[Dict[str, Any]] = None,
        labels: Optional[Dict[str, Any]] = None,
        artifacts: Optional[List[Dict[str, Any]]] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO task_results(
              task_id, case_id, case_version, case_name, plan_id, plugin, target_id,
              status, attempt, started_at, finished_at, duration_ms,
              error_code, error_message, error_stack,
              params, run_output, labels, artifacts, trace_id, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(task_id) DO UPDATE SET
              case_version=excluded.case_version,
              case_name=excluded.case_name,
              plan_id=excluded.plan_id,
              plugin=excluded.plugin,
              target_id=excluded.target_id,
              status=excluded.status,
              attempt=excluded.attempt,
              started_at=excluded.started_at,
              finished_at=excluded.finished_at,
              duration_ms=excluded.duration_ms,
              error_code=excluded.error_code,
              error_message=excluded.error_message,
              error_stack=excluded.error_stack,
              params=excluded.params,
              run_output=excluded.run_output,
              labels=excluded.labels,
              artifacts=excluded.artifacts,
              trace_id=excluded.trace_id
            """,
            (
                task_id, case_id, case_version, case_name, plan_id, plugin, target_id,
                status, attempt, started_at, finished_at, duration_ms,
                error_code, error_message, error_stack,
                _json(params), _json(run_output), _json(labels), _json(artifacts), trace_id,
                time.time(),
            ),
        )

    def mark_status(
        self, task_id: str, status: str,
        *, error_code: str | None = None, error_message: str | None = None,
    ) -> None:
        self._conn.execute(
            "UPDATE task_results SET status=?, error_code=COALESCE(?, error_code), "
            "error_message=COALESCE(?, error_message) WHERE task_id=?",
            (status, error_code, error_message, task_id),
        )

    # ---- 读 ----
    def get(self, task_id: str) -> Optional[ResultRow]:
        cur = self._conn.execute("SELECT * FROM task_results WHERE task_id=?", (task_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return _row_to_obj(row)

    def list_by_case(self, case_id: str, *, limit: int = 50) -> List[ResultRow]:
        cur = self._conn.execute(
            "SELECT * FROM task_results WHERE case_id=? "
            "ORDER BY COALESCE(started_at, created_at) DESC LIMIT ?",
            (case_id, limit),
        )
        return [_row_to_obj(r) for r in cur.fetchall()]

    def list_by_plan(self, plan_id: str, *, limit: int = 1000) -> List[ResultRow]:
        cur = self._conn.execute(
            "SELECT * FROM task_results WHERE plan_id=? "
            "ORDER BY COALESCE(started_at, created_at) DESC LIMIT ?",
            (plan_id, limit),
        )
        return [_row_to_obj(r) for r in cur.fetchall()]

    def list_by_status(self, status: str, *, limit: int = 1000) -> List[ResultRow]:
        cur = self._conn.execute(
            "SELECT * FROM task_results WHERE status=? "
            "ORDER BY COALESCE(started_at, created_at) DESC LIMIT ?",
            (status, limit),
        )
        return [_row_to_obj(r) for r in cur.fetchall()]

    def summary(self, plan_id: Optional[str] = None) -> Dict[str, int]:
        if plan_id:
            cur = self._conn.execute(
                "SELECT status, COUNT(*) c FROM task_results WHERE plan_id=? GROUP BY status",
                (plan_id,),
            )
        else:
            cur = self._conn.execute("SELECT status, COUNT(*) c FROM task_results GROUP BY status")
        return {r["status"]: r["c"] for r in cur.fetchall()}

    def recent(self, limit: int = 100) -> List[ResultRow]:
        cur = self._conn.execute(
            "SELECT * FROM task_results ORDER BY COALESCE(started_at, created_at) DESC LIMIT ?",
            (limit,),
        )
        return [_row_to_obj(r) for r in cur.fetchall()]


def _row_to_obj(row: sqlite3.Row) -> ResultRow:
    return ResultRow(
        task_id=row["task_id"],
        case_id=row["case_id"],
        case_version=row["case_version"],
        case_name=row["case_name"] or "",
        plan_id=row["plan_id"],
        plugin=row["plugin"],
        target_id=row["target_id"],
        status=row["status"],
        attempt=row["attempt"] or 1,
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        duration_ms=row["duration_ms"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        error_stack=row["error_stack"],
        params=_loads(row["params"]) or {},
        run_output=_loads(row["run_output"]) or {},
        labels=_loads(row["labels"]) or {},
        artifacts=_loads(row["artifacts"]) or [],
        trace_id=row["trace_id"],
        created_at=row["created_at"],
    )
