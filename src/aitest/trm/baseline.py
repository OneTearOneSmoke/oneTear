"""基线对比。

按 [`test-report-management-design.md`](../docs/ai-test/test-report-management-design.md) §7.4：

  给两个 run（或两个 plan_id），按 case_id 对齐状态，产出 4 类变更：
    - NEW_FAILURE  : 新增失败（基线成功、当前失败）
    - REGRESSION   : 新通过 → 已回归（基线失败、当前又失败；或新失败）
    - FIXED        : 已修复（基线失败、当前成功）
    - NEW_PASS     : 新增通过（基线无该 case、当前成功）
    - STILL_FAIL   : 仍失败
    - STILL_PASS   : 仍通过

每个变更携带 status diff + 时间戳，便于报告渲染。
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .analyzer import Analyzer, AnalyzerResult


@dataclass
class BaselineDiff:
    case_id: str
    kind: str                    # NEW_FAILURE / REGRESSION / FIXED / NEW_PASS / STILL_FAIL / STILL_PASS / MISSING
    baseline_status: Optional[str]
    current_status: Optional[str]
    error_code: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BaselineConfig:
    fail_statuses: tuple = ("FAILED", "TIMEOUT", "ERROR")
    pass_statuses: tuple = ("SUCCESS",)


class BaselineComparator(Analyzer):
    name = "baseline"

    def __init__(self, *, config: Optional[BaselineConfig] = None) -> None:
        self.config = config or BaselineConfig()

    # ---- public ----
    def compare(
        self,
        store: Any,
        *,
        baseline_plan_id: str,
        current_plan_id: str,
        config: Optional[BaselineConfig] = None,
    ) -> List[BaselineDiff]:
        cfg = config or self.config
        baseline = self._last_status_per_case(store, baseline_plan_id)
        current = self._last_status_per_case(store, current_plan_id)

        diffs: List[BaselineDiff] = []
        all_cases = set(baseline) | set(current)

        for cid in sorted(all_cases):
            b = baseline.get(cid)
            c = current.get(cid)
            b_status = b["status"] if b else None
            c_status = c["status"] if c else None
            b_pass = b_status in cfg.pass_statuses if b_status else False
            b_fail = b_status in cfg.fail_statuses if b_status else False
            c_pass = c_status in cfg.pass_statuses if c_status else False
            c_fail = c_status in cfg.fail_statuses if c_status else False

            kind = self._classify(b_pass, b_fail, c_pass, c_fail, b_status, c_status)
            err = c["error_code"] if c else (b["error_code"] if b else None)
            diffs.append(
                BaselineDiff(
                    case_id=cid,
                    kind=kind,
                    baseline_status=b_status,
                    current_status=c_status,
                    error_code=err,
                )
            )
        return diffs

    def run(
        self,
        store: Any,
        baseline_plan_id: str,
        current_plan_id: str,
        config: Optional[BaselineConfig] = None,
        **kwargs: Any,
    ) -> AnalyzerResult:
        diffs = self.compare(
            store,
            baseline_plan_id=baseline_plan_id,
            current_plan_id=current_plan_id,
            config=config,
        )
        counts: Dict[str, int] = {}
        for d in diffs:
            counts[d.kind] = counts.get(d.kind, 0) + 1

        recs: List[str] = []
        for d in diffs:
            if d.kind in ("NEW_FAILURE", "REGRESSION"):
                recs.append(
                    f"{d.kind}: case {d.case_id} {d.baseline_status} → {d.current_status}"
                )
        return AnalyzerResult(
            name=self.name,
            summary=(
                f"{len(diffs)} cases compared · "
                f"new_failure={counts.get('NEW_FAILURE',0)}, "
                f"fixed={counts.get('FIXED',0)}, "
                f"regression={counts.get('REGRESSION',0)}"
            ),
            data={
                "baseline_plan_id": baseline_plan_id,
                "current_plan_id": current_plan_id,
                "counts": counts,
                "items": [d.to_dict() for d in diffs],
            },
            recommendations=recs[:20],
        )

    # ---- helpers ----
    def _classify(
        self,
        b_pass: bool, b_fail: bool,
        c_pass: bool, c_fail: bool,
        b_status: Optional[str], c_status: Optional[str],
    ) -> str:
        if b_status is None and c_status is not None:
            return "NEW_PASS" if c_pass else "NEW_FAILURE"
        if c_status is None and b_status is not None:
            return "MISSING"
        if b_pass and c_fail:
            return "NEW_FAILURE"
        if b_fail and c_pass:
            return "FIXED"
        if b_fail and c_fail:
            # 基线失败、当前失败：分两种 — 同 status = 仍失败；新 status = 回归
            return "STILL_FAIL" if b_status == c_status else "REGRESSION"
        if b_pass and c_pass:
            return "STILL_PASS"
        return "OTHER"

    def _last_status_per_case(self, store: Any, plan_id: str) -> Dict[str, dict]:
        """对每个 case 取最近一条结果（按 started_at DESC）。"""
        if not hasattr(store, "list_by_plan"):
            raise TypeError("store must implement list_by_plan")
        rows = store.list_by_plan(plan_id, limit=100000)
        latest: Dict[str, dict] = {}
        for r in rows:
            row = r if isinstance(r, dict) else r.to_dict()
            cid = row["case_id"]
            ts = row.get("started_at") or row.get("created_at") or 0
            if cid not in latest or ts > (latest[cid].get("started_at") or latest[cid].get("created_at") or 0):
                latest[cid] = row
        return latest
