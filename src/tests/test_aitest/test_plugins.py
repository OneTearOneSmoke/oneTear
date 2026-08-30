"""PLG (Plugin) 子系统单测 —— 内置 db_sqlite 插件。"""
from __future__ import annotations
import pytest

from aitest.plugins.db_sqlite import build_registry, DB_SQLITE_MANIFEST
from aitest.plugins.discovery import list_builtin, list_manifests, get
from aitest.core.context import Context
from aitest.core.errors import CommandFailure, AssertFailure


@pytest.fixture
def reg():
    return build_registry()


@pytest.fixture
def ctx():
    c = Context()
    c.meta["__registry__"] = build_registry()
    return c


# ──────────── Discovery ────────────

class TestDiscovery:
    def test_list_builtin_has_db_sqlite(self):
        names = {p.name for p in list_builtin()}
        assert "db_sqlite" in names

    def test_list_manifests_serializable(self):
        out = list_manifests()
        assert isinstance(out, list)
        assert out[0]["name"] == "db_sqlite"
        assert "db.connect" in out[0]["commands"]

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError):
            get("nope")


# ──────────── DB connect / close ────────────

class TestDBConnect:
    def test_connect_creates_connection(self, reg, ctx):
        from aitest.plugins import db_sqlite
        # 每个测试用独立 alias 隔离状态
        db_sqlite._CONNS.clear()
        out = reg.get_command("db.connect").run({"alias": "main", "path": ":memory:"}, ctx)
        assert out["ok"] is True
        assert "main" in db_sqlite._CONNS

    def test_close_returns_true(self, reg, ctx):
        from aitest.plugins import db_sqlite
        db_sqlite._CONNS.clear()
        reg.get_command("db.connect").run({"alias": "main", "path": ":memory:"}, ctx)
        out = reg.get_command("db.close").run({"alias": "main"}, ctx)
        assert out["closed"] is True
        assert "main" not in db_sqlite._CONNS

    def test_close_unknown_returns_false(self, reg, ctx):
        out = reg.get_command("db.close").run({"alias": "missing"}, ctx)
        assert out["closed"] is False

    def test_query_without_connect_raises(self, reg, ctx):
        with pytest.raises(CommandFailure, match="no connection"):
            reg.get_command("db.query").run({"sql": "SELECT 1"}, ctx)


# ──────────── DB exec / query ────────────

class TestDBExecQuery:
    def _bootstrap(self, reg, ctx):
        reg.get_command("db.connect").run({"alias": "main", "path": ":memory:"}, ctx)
        reg.get_command("db.exec").run({
            "alias": "main",
            "sql": "CREATE TABLE t(id INTEGER PRIMARY KEY, name TEXT, age INTEGER)",
        }, ctx)
        for name, age in [("a", 1), ("b", 2), ("c", 3)]:
            reg.get_command("db.exec").run({
                "alias": "main",
                "sql": "INSERT INTO t(name, age) VALUES (?, ?)",
                "params": [name, age],
            }, ctx)

    def test_exec_returns_rowcount(self, reg, ctx):
        self._bootstrap(reg, ctx)
        out = reg.get_command("db.exec").run({
            "alias": "main",
            "sql": "DELETE FROM t WHERE id = 1",
        }, ctx)
        assert out["rowcount"] == 1

    def test_query_returns_rows(self, reg, ctx):
        self._bootstrap(reg, ctx)
        out = reg.get_command("db.query").run({
            "alias": "main",
            "sql": "SELECT * FROM t ORDER BY id",
        }, ctx)
        assert out["rowcount"] == 3
        assert "name" in out["columns"]
        assert out["rows"][0]["name"] == "a"

    def test_tables(self, reg, ctx):
        self._bootstrap(reg, ctx)
        out = reg.get_command("db.tables").run({"alias": "main"}, ctx)
        assert "t" in out["tables"]


# ──────────── Assertors ────────────

class TestDBAssertors:
    def _bootstrap(self, reg, ctx):
        reg.get_command("db.connect").run({"alias": "main", "path": ":memory:"}, ctx)
        reg.get_command("db.exec").run({
            "alias": "main",
            "sql": "CREATE TABLE t(id INTEGER PRIMARY KEY, name TEXT, age INTEGER)",
        }, ctx)
        for name, age in [("a", 1), ("b", 2), ("c", 3)]:
            reg.get_command("db.exec").run({
                "alias": "main",
                "sql": "INSERT INTO t(name, age) VALUES (?, ?)",
                "params": [name, age],
            }, ctx)

    def test_row_count_pass(self, reg, ctx):
        self._bootstrap(reg, ctx)
        reg.get_assertor("db.row_count").check({
            "alias": "main", "sql": "SELECT * FROM t", "expect": 3,
        }, ctx)

    def test_row_count_fail(self, reg, ctx):
        self._bootstrap(reg, ctx)
        with pytest.raises(AssertFailure):
            reg.get_assertor("db.row_count").check({
                "alias": "main", "sql": "SELECT * FROM t", "expect": 99,
            }, ctx)

    def test_cell_eq_pass(self, reg, ctx):
        self._bootstrap(reg, ctx)
        reg.get_assertor("db.cell_eq").check({
            "alias": "main", "sql": "SELECT * FROM t ORDER BY id",
            "row": 1, "col": "name", "expect": "b",
        }, ctx)

    def test_cell_eq_fail(self, reg, ctx):
        self._bootstrap(reg, ctx)
        with pytest.raises(AssertFailure):
            reg.get_assertor("db.cell_eq").check({
                "alias": "main", "sql": "SELECT * FROM t ORDER BY id",
                "row": 0, "col": "name", "expect": "wrong",
            }, ctx)

    def test_col_eq_all_match(self, reg, ctx):
        self._bootstrap(reg, ctx)
        reg.get_assertor("db.col_eq").check({
            "alias": "main", "sql": "SELECT * FROM t WHERE id = 1",
            "col": "name", "expect": "a",
        }, ctx)

    def test_col_eq_partial_mismatch_raises(self, reg, ctx):
        self._bootstrap(reg, ctx)
        with pytest.raises(AssertFailure):
            reg.get_assertor("db.col_eq").check({
                "alias": "main", "sql": "SELECT * FROM t",
                "col": "age", "expect": 99,
            }, ctx)


# ──────────── Manifest ────────────

class TestManifest:
    def test_manifest_keys(self):
        for k in ("name", "version", "description", "commands", "assertors"):
            assert k in DB_SQLITE_MANIFEST

    def test_manifest_commands_unique(self):
        cmds = DB_SQLITE_MANIFEST["commands"]
        assert len(cmds) == len(set(cmds))
