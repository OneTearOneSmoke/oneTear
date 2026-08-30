"""Flaky 检测器。

按 [`test-report-management-design.md`](../docs/ai-test/test-report-management-design.md) §7.3：

  - 同一 case 在最近 N（默认 50）次执行中，状态既有 SUCCESS 又有 FAILED
  - 失败比例 ∈ [min_ratio, max_ratio]（默认 [0.05, 0.50]）
  - 命中 → 标记 flaky
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional

from .analyzer import Analyzer, AnalyzerResult


@dataclass
class FlakyCase:
    case_id: str
    window: int                 # 实际看的最近执行次数
    successes: int
    failures: int
    other: int                   # TIMEOUT / CANCELED / ERROR / BLOCKED
    fail_ratio: float            # failures / window
    last_status: str
    last_at: Optional[float]

    @property
    def is_flaky(self) -> bool:
        return self.successes > 0 and self.failures > 0 and 0.0 < self.fail_ratio < 1.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["is_flaky"] = self.is_flaky
        return d


@dataclass
class FlakyConfig:
    window: int = 50
    min_ratio: float = 0.05
    max_ratio: float = 0.50
    fail_statuses: tuple = ("FAILED", "TIMEOUT", "ERROR")
    pass_statuses: tuple = ("SUCCESS",)


class FlakyDetector(Analyzer):
    """滑动窗口 flaky 检测。

    用法::

        det = FlakyDetector(min_ratio=0.1, max_ratio=0.6)
        result = det.run(store=my_store, plan_id=None, config=FlakyConfig())
    """

    name = "flaky"

    def __init__(self, *, min_ratio: float = 0.05, max_ratio: float = 0.50) -> None:
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio

    def _default_config(self) -> FlakyConfig:
        return FlakyConfig(
            window=50,
            min_ratio=self.min_ratio,
            max_ratio=self.max_ratio,
        )

    def detect(
        self,
        store: Any,
        *,
        plan_id: Optional[str] = None,
        config: Optional[FlakyConfig] = None,
    ) -> List[FlakyCase]:
        cfg = config or self._default_config()
        cases = self._collect_cases(store, plan_id=plan_id, limit_per_case=cfg.window)
        results: List[FlakyCase] = []
        for case_id, rows in cases.items():
            successes = sum(1 for r in rows if r["status"] in cfg.pass_statuses)
            failures = sum(1 for r in rows if r["status"] in cfg.fail_statuses)
            other = len(rows) - successes - failures
            window = len(rows)
            fail_ratio = (failures / window) if window else 0.0
            last = rows[0]  # 已按时间倒序
            results.append(
                FlakyCase(
                    case_id=case_id,
                    window=window,
                    successes=successes,
                    failures=failures,
                    other=other,
                    fail_ratio=round(fail_ratio, 4),
                    last_status=last["status"],
                    last_at=last.get("started_at") or last.get("created_at"),
                )
            )
        # 只保留 is_flaky 且比例落在 [min_ratio, max_ratio] 的
        return [
            c for c in results
            if c.is_flaky and cfg.min_ratio <= c.fail_ratio <= cfg.max_ratio
        ]

    def run(
        self,
        store: Any,
        plan_id: Optional[str] = None,
        config: Optional[FlakyConfig] = None,
        **kwargs: Any,
    ) -> AnalyzerResult:
        flaky = self.detect(store, plan_id=plan_id, config=config)
        recs: List[str] = []
        for f in flaky[:5]:
            recs.append(
                f"case {f.case_id}: 失败 {f.failures}/{f.window} "
                f"({f.fail_ratio*100:.1f}%) → 标记 flaky，建议加 @retry 或环境隔离"
            )
        return AnalyzerResult(
            name=self.name,
            summary=f"{len(flaky)} flaky cases detected",
            data={
                "count": len(flaky),
                "items": [c.to_dict() for c in flaky],
                "config": (config or self._default_config()).__dict__,
            },
            recommendations=recs,
        )

    # ---- helpers ----
    def _collect_cases(
        self,
        store: Any,
        *,
        plan_id: Optional[str],
        limit_per_case: int,
    ) -> Dict[str, List[dict]]:
        """从 store 抓每个 case 最近 N 条；可走 SQL 也可走 ORM API。"""
        cases: Dict[str, List[dict]] = {}
        # 兼容两种 store：EXF ResultStore / 自带 list_recent
        if hasattr(store, "recent"):
            rows = store.recent(limit=100000)
        else:
            rows = store.list_recent(limit=100000)  # type: ignore[attr-defined]
        for r in rows:
            cid = r.get("case_id") if isinstance(r, dict) else getattr(r, "case_id", None)
            if not cid:
                continue
            pid = r.get("plan_id") if isinstance(r, dict) else getattr(r, "plan_id", None)
            if plan_id is not None and pid != plan_id:
                continue
            cases.setdefault(cid, []).append(
                r if isinstance(r, dict) else r.to_dict()
            )
        # 每 case 按时间倒序、截断到 window
        out: Dict[str, List[dict]] = {}
        for cid, items in cases.items():
            items.sort(
                key=lambda x: x.get("started_at") or x.get("created_at") or 0,
                reverse=True,
            )
            out[cid] = items[:limit_per_case]
        return out
