"""JSON-over-stdio 协议定义。"""
from __future__ import annotations
import json
from typing import Any, Dict, Optional


def encode(obj: Dict[str, Any]) -> bytes:
    return (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")


def decode_line(line) -> Dict[str, Any]:
    if isinstance(line, bytes):
        return json.loads(line.decode("utf-8").rstrip("\n"))
    return json.loads(str(line).rstrip("\n"))


def make_request(req_id: str, op: str, **payload: Any) -> Dict[str, Any]:
    return {"id": req_id, "op": op, **payload}


def make_response_ok(req_id: str, output: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"id": req_id, "ok": True, "output": output or {}}


def make_response_err(req_id: str, code: str, message: str) -> Dict[str, Any]:
    return {
        "id": req_id,
        "ok": False,
        "error": {"code": code, "message": message},
    }
