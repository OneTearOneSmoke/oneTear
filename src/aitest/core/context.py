"""执行上下文：在 Runner 内部贯穿 case / params / run / meta。"""
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Context:
    case: Any = None
    params: Dict[str, Any] = field(default_factory=dict)
    run: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
    env: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        meta = {k: v for k, v in self.meta.items() if not k.startswith("__")}
        return {
            "case": self.case.id if self.case else None,
            "params": self.params,
            "run": self.run,
            "meta": meta,
        }
