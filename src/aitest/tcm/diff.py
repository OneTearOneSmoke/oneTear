"""Case Diff —— 用例级 diff（语义 + 原始）。

按 [`test-case-management-design.md`](../docs/ai-test/test-case-management-design.md) §diff：

    - tags / severity / owner / description / timeout / retries    → meta 字段 diff
    - run / fixture.* / asserts                                     → steps diff
    - params                                                       → params diff

返回结构：
    CaseDiff {
      id, meta: dict[path → (old, new)],
      steps: list[(field, kind, ...)],
      identical: bool
    }

模块边界：不依赖 EXF / TRM / TMRM；纯数据对比。
"""
from __future__ import annotations
import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .case import Case
from .version import content_hash


# meta 字段 = 直接可比较的标量
META_FIELDS = (
    "name", "tags", "params", "severity", "owner",
    "timeout", "retries", "description", "source",
)

# steps 字段 = 嵌套 step 对象列表
STEP_FIELDS = ("fixture_setup", "fixture_teardown", "run", "asserts")


@dataclass
class StepDiff:
    field: str
    kind: str         # added / removed / changed
    before: Any = None
    after: Any = None
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "kind": self.kind,
            "note": self.note,
            "before": self.before,
            "after": self.after,
        }


@dataclass
class CaseDiff:
    case_id: str
    identical: bool
    meta: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)
    steps: List[StepDiff] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "identical": self.identical,
            "meta": [
                {"field": k, "before": v[0], "after": v[1]}
                for k, v in self.meta.items()
            ],
            "steps": [s.to_dict() for s in self.steps],
        }


def diff_cases(a: Case, b: Case) -> CaseDiff:
    """按 id 对齐两个 Case，产出 diff。"""
    if a.id != b.id:
        raise ValueError(f"case id mismatch: {a.id} != {b.id}")
    cd = CaseDiff(case_id=a.id, identical=True)

    # meta 字段
    for f in META_FIELDS:
        va = getattr(a, f, None)
        vb = getattr(b, f, None)
        if va != vb:
            cd.meta[f] = (va, vb)

    # steps 字段
    before = {
        "run": a.run.to_dict() if a.run else None,
        "fixture_setup": [s.to_dict() for s in (a.fixture_setup or [])],
        "fixture_teardown": [s.to_dict() for s in (a.fixture_teardown or [])],
        "asserts": [s.to_dict() for s in (a.asserts or [])],
    }
    after = {
        "run": b.run.to_dict() if b.run else None,
        "fixture_setup": [s.to_dict() for s in (b.fixture_setup or [])],
        "fixture_teardown": [s.to_dict() for s in (b.fixture_teardown or [])],
        "asserts": [s.to_dict() for s in (b.asserts or [])],
    }
    for f in ("run", "fixture_setup", "fixture_teardown", "asserts"):
        if before[f] != after[f]:
            cd.steps.append(
                StepDiff(
                    field=f,
                    kind="changed",
                    before=before[f],
                    after=after[f],
                    note=f"{len(before[f]) if isinstance(before[f], list) else '-'} → "
                         f"{len(after[f]) if isinstance(after[f], list) else '-'}",
                )
            )

    cd.identical = not cd.meta and not cd.steps
    return cd


def diff_suites(sa, sb) -> List[CaseDiff]:
    """按 id 对齐两 Suite，产出 list[CaseDiff]。"""
    a_map = {c.id: c for c in sa.cases}
    b_map = {c.id: c for c in sb.cases}
    ids = sorted(set(a_map) | set(b_map))
    out: List[CaseDiff] = []
    for cid in ids:
        a = a_map.get(cid)
        b = b_map.get(cid)
        if a is None and b is not None:
            out.append(CaseDiff(
                case_id=cid, identical=False,
                steps=[StepDiff(field="case", kind="added", before=None, after=b.to_dict())],
            ))
        elif a is not None and b is None:
            out.append(CaseDiff(
                case_id=cid, identical=False,
                steps=[StepDiff(field="case", kind="removed", before=a.to_dict(), after=None)],
            ))
        else:
            out.append(diff_cases(a, b))
    return out
