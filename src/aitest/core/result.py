"""用例执行结果。"""
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Result:
    case_id: str
    case_name: str
    ok: bool
    status: str
    ctx: Any
    error: Optional[BaseException] = None
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "ok": self.ok,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "error": str(self.error) if self.error else None,
            "ctx": self.ctx.as_dict() if self.ctx else {},
        }
