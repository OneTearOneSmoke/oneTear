"""db_sqlite 插件 e2e demo —— 直接调 Registry（不走 stdio）。

模拟一个用例：
  - id: db.demo
  - run:  db.connect :memory:
  - 然后 db.exec 建表 + 插数据
  - asserts:
      - db.row_count:  expect=3
      - db.cell_eq:    row=0, col=name, expect='alice'
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aitest.plugins.db_sqlite import build_registry
from aitest.core.context import Context
from aitest.core.errors import AssertFailure


def invoke(reg, ctx, op, args):
    """op = 'cmd:db.connect' 或 'assert:db.row_count'"""
    kind, name = op.split(":", 1)
    if kind == "cmd":
        return reg.get_command(name).run(args or {}, ctx)
    if kind == "assert":
        reg.get_assertor(name).check(args or {}, ctx)
        return "pass"
    raise ValueError(op)


def main() -> int:
    reg = build_registry()
    ctx = Context()
    ctx.meta["__registry__"] = reg

    print("=== 1) connect :memory: + 建表 ===")
    print("  ", invoke(reg, ctx, "cmd:db.connect", {"alias": "main", "path": ":memory:"}))
    print("  ", invoke(reg, ctx, "cmd:db.exec", {
        "alias": "main",
        "sql": "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT, age INTEGER)",
    }))

    print("=== 2) insert 3 rows ===")
    for name, age in [("alice", 30), ("bob", 25), ("carol", 40)]:
        print("  ", invoke(reg, ctx, "cmd:db.exec", {
            "alias": "main",
            "sql": "INSERT INTO users(name, age) VALUES (?, ?)",
            "params": [name, age],
        }))

    print("=== 3) query + assert row count = 3 ===")
    out = invoke(reg, ctx, "cmd:db.query", {"alias": "main", "sql": "SELECT * FROM users"})
    print(f"  rows: {out['rowcount']}, cols: {out['columns']}")
    invoke(reg, ctx, "assert:db.row_count", {
        "alias": "main", "sql": "SELECT * FROM users", "expect": 3,
    })
    print("  assert db.row_count PASS")

    print("=== 4) assert row 0, col name = alice ===")
    invoke(reg, ctx, "assert:db.cell_eq", {
        "alias": "main", "sql": "SELECT * FROM users ORDER BY id",
        "row": 0, "col": "name", "expect": "alice",
    })
    print("  assert db.cell_eq PASS")

    print("=== 5) assert all ages > 20 (db.col_eq, only alice=30) ===")
    try:
        invoke(reg, ctx, "assert:db.col_eq", {
            "alias": "main", "sql": "SELECT * FROM users",
            "col": "age", "expect": 30,
        })
        print("  assert db.col_eq PASS (unexpected)")
    except AssertFailure as e:
        print(f"  assert db.col_eq FAIL (expected): {e}")

    print("=== 6) db.tables ===")
    print("  ", invoke(reg, ctx, "cmd:db.tables", {"alias": "main"}))

    print("=== 7) db.close ===")
    print("  ", invoke(reg, ctx, "cmd:db.close", {"alias": "main"}))

    print("[done] demo finished (step 5 expected to fail)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
