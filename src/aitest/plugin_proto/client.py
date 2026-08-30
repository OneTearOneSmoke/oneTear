"""插件客户端：父进程通过子进程 stdio 与插件通信。"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import threading
import uuid
from typing import Any, Dict, List, Optional


class PluginClient:
    """通过 stdio JSON-RPC 与插件子进程通信。

    使用：
        client = PluginClient(["python", "-m", "aitest.plugin_proto.server"])
        manifest = client.manifest()
        out = client.invoke("shell.run", {"cmd": "echo hi"}, ctx={})
        client.close()
    """

    def __init__(self, cmd: List[str], *, env: Optional[Dict[str, str]] = None,
                 cwd: Optional[str] = None, timeout: float = 30.0) -> None:
        self.cmd = cmd
        self.timeout = timeout
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, **(env or {})},
            cwd=cwd,
            bufsize=0,
        )
        self._lock = threading.Lock()
        self._closed = False
        self._manifest_cache: Optional[Dict[str, Any]] = None

    # ---- API ----
    def manifest(self) -> Dict[str, Any]:
        if self._manifest_cache is not None:
            return self._manifest_cache
        resp = self._roundtrip(make_request("manifest", op="manifest"))
        if not resp.get("ok"):
            raise RuntimeError(f"manifest failed: {resp.get('error')}")
        self._manifest_cache = resp.get("output") or {}
        return self._manifest_cache

    def invoke(self, name: str, args: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._roundtrip(make_request(uuid.uuid4().hex, op="invoke", cmd=name, args=args, ctx=ctx or {}))

    def check(self, assertor: str, args: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._roundtrip(make_request(uuid.uuid4().hex, op="assert", assertor=assertor, args=args, ctx=ctx or {}))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._proc.terminate()
            self._proc.wait(timeout=2)
        except Exception:  # noqa: BLE001
            try:
                self._proc.kill()
            except Exception:  # noqa: BLE001
                pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---- 内部 ----
    def _roundtrip(self, req: Dict[str, Any]) -> Dict[str, Any]:
        if self._closed:
            raise RuntimeError("client closed")
        line = (json.dumps(req, ensure_ascii=False) + "\n").encode("utf-8")
        with self._lock:
            try:
                self._proc.stdin.write(line)
                self._proc.stdin.flush()
            except BrokenPipeError as e:
                raise RuntimeError(f"plugin died: {e}")
            # 读一行响应
            raw = self._proc.stdout.readline()
            if not raw:
                stderr = self._proc.stderr.read().decode("utf-8", errors="replace") if self._proc.stderr else ""
                raise RuntimeError(f"plugin closed: {stderr[:200]}")
            return json.loads(raw.decode("utf-8").rstrip("\n"))


def make_request(req_id: str, *, op: str, **payload: Any) -> Dict[str, Any]:
    from .protocol import make_request as _make
    return _make(req_id, op, **payload)
