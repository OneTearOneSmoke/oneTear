"""db_sqlite 走 stdio JSON 协议的 e2e demo。

启动 PluginServer(--plugin=db_sqlite)，通过 PluginClient 远程调用，验证
整个 stdio 通道 + 真实 db_sqlite 插件。
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aitest.plugin_proto.client import PluginClient


def _out(r):
    if not r.get("ok"):
        raise RuntimeError(f"rpc fail: {r.get('error')}")
    return r.get("output") or {}


def main() -> int:
    client = PluginClient([
        sys.executable, "-m", "aitest", "plugin-server", "--plugin", "db_sqlite",
    ])

    try:
        # 1) manifest
        m = client.manifest()
        print("[1] manifest.commands=", m["commands"])
        print("    manifest.assertors=", m["assertors"])
        assert "db.connect" in m["commands"]
        assert "db.row_count" in m["assertors"]

        # 2) connect
        r = client.invoke("db.connect", {"alias": "main", "path": ":memory:"})
        out = _out(r)
        print(f"[2] connect: {out}")
        assert out.get("ok") is True

        # 3) exec
        r = client.invoke("db.exec", {
            "alias": "main",
            "sql": "CREATE TABLE kv(k TEXT PRIMARY KEY, v INTEGER)",
        })
        print(f"[3] create: {_out(r)}")

        r = client.invoke("db.exec", {
            "alias": "main",
            "sql": "INSERT INTO kv VALUES ('x', 42)",
        })
        print(f"[4] insert: {_out(r)}")

        # 5) query
        r = client.invoke("db.query", {"alias": "main", "sql": "SELECT * FROM kv"})
        out = _out(r)
        print(f"[5] query: {out}")
        assert out["rowcount"] == 1
        assert out["rows"][0]["k"] == "x"

        # 6) row_count assert
        r = client.check("db.row_count", {
            "alias": "main", "sql": "SELECT * FROM kv", "expect": 1,
        })
        out = _out(r)
        print(f"[6] row_count: {out}")
        assert out["passed"]

        print("[done] stdio plugin-server roundtrip OK")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
