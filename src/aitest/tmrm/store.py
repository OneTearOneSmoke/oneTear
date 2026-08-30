"""TMRM SQLite 注册表（轻量原型；v1.0 切到 Postgres + Redis）。"""
from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .machine import Machine, MachineStatus, MachineType
from .pool import Pool
from .session import Session, SessionStatus


SCHEMA = """
CREATE TABLE IF NOT EXISTS machines (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  spec TEXT,
  status TEXT NOT NULL,
  provider TEXT,
  region TEXT,
  zone TEXT,
  image TEXT,
  labels TEXT,
  pool_id TEXT,
  last_heartbeat REAL,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_machine_status ON machines(status);
CREATE INDEX IF NOT EXISTS idx_machine_type   ON machines(type);
CREATE INDEX IF NOT EXISTS idx_machine_pool   ON machines(pool_id);

CREATE TABLE IF NOT EXISTS pools (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  selectors TEXT,
  description TEXT,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  machine_id TEXT NOT NULL,
  owner TEXT NOT NULL,
  plan_id TEXT,
  task_id TEXT,
  acquired_at REAL NOT NULL,
  released_at REAL,
  status TEXT NOT NULL,
  ttl_seconds REAL
);
CREATE INDEX IF NOT EXISTS idx_session_machine ON sessions(machine_id);
CREATE INDEX IF NOT EXISTS idx_session_owner   ON sessions(owner);
CREATE INDEX IF NOT EXISTS idx_session_status  ON sessions(status);

CREATE TABLE IF NOT EXISTS health_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  machine_id TEXT NOT NULL,
  at REAL NOT NULL,
  status TEXT NOT NULL,
  latency_ms INTEGER,
  error TEXT
);
CREATE INDEX IF NOT EXISTS idx_health_machine ON health_records(machine_id);
"""


def _connect(path: str) -> sqlite3.Connection:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _j(obj: Any) -> str:
    if obj is None:
        return ""
    return json.dumps(obj, ensure_ascii=False, default=str)


def _jl(s: Optional[str]) -> Any:
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:  # noqa: BLE001
        return {}


class FarmStore:
    """Farm SQLite 注册表。"""

    def __init__(self, path: str = "aitest-farm.db") -> None:
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

    # ---- machines ----
    def upsert_machine(self, m: Machine) -> None:
        self._conn.execute(
            """
            INSERT INTO machines(id, name, type, spec, status, provider, region, zone,
                                 image, labels, pool_id, last_heartbeat, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
              name=excluded.name,
              type=excluded.type,
              spec=excluded.spec,
              status=excluded.status,
              provider=excluded.provider,
              region=excluded.region,
              zone=excluded.zone,
              image=excluded.image,
              labels=excluded.labels,
              pool_id=excluded.pool_id,
              last_heartbeat=excluded.last_heartbeat
            """,
            (
                m.id, m.name, m.type.value, _j(m.spec), m.status.value,
                m.provider, m.region, m.zone, m.image,
                _j(m.labels), m.pool_id, m.last_heartbeat, m.created_at,
            ),
        )

    def get_machine(self, machine_id: str) -> Optional[Machine]:
        cur = self._conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,))
        row = cur.fetchone()
        return _machine_from_row(row) if row else None

    def list_machines(
        self,
        *,
        status: Optional[MachineStatus] = None,
        machine_type: Optional[MachineType] = None,
        pool_id: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Machine]:
        clauses = []
        params: list = []
        if status is not None:
            clauses.append("status=?")
            params.append(status.value)
        if machine_type is not None:
            clauses.append("type=?")
            params.append(machine_type.value)
        if pool_id is not None:
            clauses.append("pool_id=?")
            params.append(pool_id)
        sql = "SELECT * FROM machines"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cur = self._conn.execute(sql, params)
        return [_machine_from_row(r) for r in cur.fetchall()]

    def delete_machine(self, machine_id: str) -> None:
        self._conn.execute("DELETE FROM machines WHERE id=?", (machine_id,))

    # ---- pools ----
    def upsert_pool(self, p: Pool) -> None:
        self._conn.execute(
            """
            INSERT INTO pools(id, name, selectors, description, created_at)
            VALUES (?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
              name=excluded.name,
              selectors=excluded.selectors,
              description=excluded.description
            """,
            (p.id, p.name, _j(p.selectors.__dict__), p.description, p.created_at),
        )

    def list_pools(self) -> List[Pool]:
        cur = self._conn.execute("SELECT * FROM pools ORDER BY created_at DESC")
        out: List[Pool] = []
        for r in cur.fetchall():
            sel_dict = _jl(r["selectors"])
            from .machine import Selector
            sel = Selector(
                type=MachineType(sel_dict["type"]) if sel_dict.get("type") else None,
                labels=sel_dict.get("labels") or {},
                pool_id=sel_dict.get("pool_id"),
                provider=sel_dict.get("provider"),
                region=sel_dict.get("region"),
            )
            out.append(
                Pool(
                    id=r["id"], name=r["name"], selectors=sel,
                    description=r["description"] or "", created_at=r["created_at"],
                )
            )
        return out

    # ---- sessions ----
    def insert_session(self, s: Session) -> None:
        self._conn.execute(
            """
            INSERT INTO sessions(id, machine_id, owner, plan_id, task_id,
                                 acquired_at, released_at, status, ttl_seconds)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                s.id, s.machine_id, s.owner, s.plan_id, s.task_id,
                s.acquired_at, s.released_at, s.status.value, s.ttl_seconds,
            ),
        )

    def get_session(self, session_id: str) -> Optional[Session]:
        cur = self._conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,))
        row = cur.fetchone()
        return _session_from_row(row) if row else None

    def list_sessions(
        self,
        *,
        owner: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 1000,
    ) -> List[Session]:
        clauses = []
        params: list = []
        if owner is not None:
            clauses.append("owner=?")
            params.append(owner)
        if status is not None:
            clauses.append("status=?")
            params.append(status.value)
        sql = "SELECT * FROM sessions"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY acquired_at DESC LIMIT ?"
        params.append(limit)
        cur = self._conn.execute(sql, params)
        return [_session_from_row(r) for r in cur.fetchall()]

    def update_session(self, s: Session) -> None:
        self._conn.execute(
            """
            UPDATE sessions SET machine_id=?, owner=?, plan_id=?, task_id=?,
                                released_at=?, status=?, ttl_seconds=?
            WHERE id=?
            """,
            (s.machine_id, s.owner, s.plan_id, s.task_id,
             s.released_at, s.status.value, s.ttl_seconds, s.id),
        )

    # ---- health ----
    def append_health(self, machine_id: str, status: str,
                      latency_ms: int = 0, error: str = "") -> None:
        self._conn.execute(
            "INSERT INTO health_records(machine_id, at, status, latency_ms, error) "
            "VALUES (?,?,?,?,?)",
            (machine_id, time.time(), status, latency_ms, error),
        )

    def recent_health(self, machine_id: str, limit: int = 20) -> List[dict]:
        cur = self._conn.execute(
            "SELECT * FROM health_records WHERE machine_id=? "
            "ORDER BY at DESC LIMIT ?",
            (machine_id, limit),
        )
        return [dict(r) for r in cur.fetchall()]


def _machine_from_row(r: sqlite3.Row) -> Machine:
    return Machine(
        id=r["id"], name=r["name"],
        type=MachineType(r["type"]),
        spec=_jl(r["spec"]),
        status=MachineStatus(r["status"]),
        provider=r["provider"], region=r["region"], zone=r["zone"],
        image=r["image"],
        labels=_jl(r["labels"]),
        pool_id=r["pool_id"],
        last_heartbeat=r["last_heartbeat"],
        created_at=r["created_at"],
    )


def _session_from_row(r: sqlite3.Row) -> Session:
    return Session(
        id=r["id"], machine_id=r["machine_id"], owner=r["owner"],
        plan_id=r["plan_id"], task_id=r["task_id"],
        acquired_at=r["acquired_at"], released_at=r["released_at"],
        status=SessionStatus(r["status"]), ttl_seconds=r["ttl_seconds"],
    )
