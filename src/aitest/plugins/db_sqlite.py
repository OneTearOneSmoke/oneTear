"""db_sqlite 插件 —— 内置 SQLite 数据库插件（stdlib only）。

Manifest:
  commands:
    - db.connect  : 建立连接
    - db.query    : 执行 SELECT，返回 rows + columns
    - db.exec     : 执行 INSERT/UPDATE/DELETE，返回 rowcount + lastrowid
    - db.close    : 关闭连接
  assertors:
    - db.row_count: 校验 query 返回的行数
    - db.cell_eq  : 校验 query 返回的指定 (row, col) 等于某值

协议：
  - 通过 Context.meta['__db_conns__'] 维护 {alias -> sqlite3.Connection}
  - 跨命令共享连接用同一 alias

样例用例：
  - id: db.basic
    run:
      cmd: db.connect
      args: { alias: main, path: ":memory:" }
    asserts:
      - row_count: { alias: main, sql: "SELECT 1", expect: 1 }
"""
from __future__ import annotations
import sqlite3
from typing import Any, Dict, List, Optional

from ..core.errors import CommandFailure, AssertFailure


DB_SQLITE_MANIFEST: dict = {
    "name": "db_sqlite",
    "version": "0.5.0",
    "description": "SQLite 数据库插件（基于 stdlib sqlite3，零外部依赖）",
    "commands": ["db.connect", "db.query", "db.exec", "db.close", "db.tables"],
    "assertors": ["db.row_count", "db.cell_eq", "db.col_eq"],
}


# ---- 连接管理 ----

# 模块级连接池 —— 在 plugin-server 长生命周期的子进程里按 alias 共享。
# 不放 ctx.meta 是因为 stdio 协议每次 invoke 都构造新 Context。
_CONNS: Dict[str, sqlite3.Connection] = {}


def _conns(ctx) -> Dict[str, sqlite3.Connection]:
    return _CONNS


# ---- commands ----

class DBConnect:
    name = "db.connect"

    def run(self, args: Dict[str, Any], ctx) -> Dict[str, Any]:
        alias = args.get("alias") or "default"
        path = args.get("path") or ":memory:"
        conns = _conns(ctx)
        if alias in conns:
            try:
                conns[alias].close()
            except Exception:  # noqa: BLE001
                pass
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conns[alias] = conn
        return {"alias": alias, "path": path, "ok": True}


class DBQuery:
    name = "db.query"

    def run(self, args: Dict[str, Any], ctx) -> Dict[str, Any]:
        alias = args.get("alias") or "default"
        sql = args.get("sql")
        params = args.get("params") or []
        if not sql:
            raise CommandFailure(self.name, "missing args.sql")
        conn = _conns(ctx).get(alias)
        if conn is None:
            raise CommandFailure(self.name, f"no connection for alias={alias!r}")
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        data = [dict(r) for r in rows]
        return {"alias": alias, "columns": cols, "rows": data, "rowcount": len(data)}


class DBExec:
    name = "db.exec"

    def run(self, args: Dict[str, Any], ctx) -> Dict[str, Any]:
        alias = args.get("alias") or "default"
        sql = args.get("sql")
        params = args.get("params") or []
        if not sql:
            raise CommandFailure(self.name, "missing args.sql")
        conn = _conns(ctx).get(alias)
        if conn is None:
            raise CommandFailure(self.name, f"no connection for alias={alias!r}")
        cur = conn.execute(sql, params)
        conn.commit()
        return {
            "alias": alias,
            "rowcount": cur.rowcount,
            "lastrowid": cur.lastrowid,
        }


class DBClose:
    name = "db.close"

    def run(self, args: Dict[str, Any], ctx) -> Dict[str, Any]:
        alias = args.get("alias") or "default"
        conns = _conns(ctx)
        conn = conns.pop(alias, None)
        if conn is None:
            return {"alias": alias, "closed": False}
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass
        return {"alias": alias, "closed": True}


class DBTables:
    name = "db.tables"

    def run(self, args: Dict[str, Any], ctx) -> Dict[str, Any]:
        alias = args.get("alias") or "default"
        conn = _conns(ctx).get(alias)
        if conn is None:
            raise CommandFailure(self.name, f"no connection for alias={alias!r}")
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return {"alias": alias, "tables": [r[0] for r in cur.fetchall()]}


# ---- assertors ----

class DBRowCount:
    name = "db.row_count"

    def check(self, args: Dict[str, Any], ctx) -> None:
        alias = args.get("alias") or "default"
        sql = args.get("sql")
        params = args.get("params") or []
        expect = args.get("expect")
        if expect is None:
            raise AssertFailure(self.name, "missing args.expect")
        conn = _conns(ctx).get(alias)
        if conn is None:
            raise AssertFailure(self.name, f"no connection for alias={alias!r}")
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        if len(rows) != int(expect):
            raise AssertFailure(
                self.name,
                f"rowcount={len(rows)} expect={expect} sql={sql!r}",
            )


class DBCellEq:
    name = "db.cell_eq"

    def check(self, args: Dict[str, Any], ctx) -> None:
        alias = args.get("alias") or "default"
        sql = args.get("sql")
        params = args.get("params") or []
        row_idx = int(args.get("row", 0))
        col = args.get("col")
        expect = args.get("expect")
        if col is None:
            raise AssertFailure(self.name, "missing args.col")
        if "expect" not in args:
            raise AssertFailure(self.name, "missing args.expect")
        conn = _conns(ctx).get(alias)
        if conn is None:
            raise AssertFailure(self.name, f"no connection for alias={alias!r}")
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        if not rows:
            raise AssertFailure(self.name, f"no rows, sql={sql!r}")
        if row_idx >= len(rows):
            raise AssertFailure(
                self.name, f"row {row_idx} out of range (have {len(rows)})"
            )
        row = rows[row_idx]
        if isinstance(col, int):
            actual = row[col]
        else:
            actual = row[col]
        if actual != expect:
            raise AssertFailure(
                self.name,
                f"cell[{row_idx}][{col!r}]={actual!r} expect={expect!r}",
            )


class DBColEq:
    """校验 query 返回的所有行某一列都等于 expect。"""

    name = "db.col_eq"

    def check(self, args: Dict[str, Any], ctx) -> None:
        alias = args.get("alias") or "default"
        sql = args.get("sql")
        params = args.get("params") or []
        col = args.get("col")
        expect = args.get("expect")
        if col is None or "expect" not in args:
            raise AssertFailure(self.name, "missing args.col or args.expect")
        conn = _conns(ctx).get(alias)
        if conn is None:
            raise AssertFailure(self.name, f"no connection for alias={alias!r}")
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        if not rows:
            raise AssertFailure(self.name, f"no rows, sql={sql!r}")
        for i, r in enumerate(rows):
            v = r[col] if isinstance(col, int) else r[col]
            if v != expect:
                raise AssertFailure(
                    self.name,
                    f"row[{i}][{col!r}]={v!r} expect={expect!r}",
                )


def build_registry():
    """返回装好 db_sqlite 的 Registry。供 plugin-server 装配使用。"""
    from ..tcm.registry import Registry
    reg = Registry()
    for c in (DBConnect, DBQuery, DBExec, DBClose, DBTables):
        reg.command(instance=c())
    for a in (DBRowCount, DBCellEq, DBColEq):
        reg.assertor(instance=a())
    return reg
