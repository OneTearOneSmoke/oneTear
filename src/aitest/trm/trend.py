"""趋势 / 健康指标。

对单个 case 给一条状态时间线 + 通过率 + 延迟分位 + 最近 flaky 标记，
供 dashboard 与 AI Agent 拉取。
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from .analyzer import Analyzer, AnalyzerResult


@dataclass
class CaseTrend:
    case_id: str
    window: int
    successes: int
    failures: int
    pass_rate: float
    durations_ms: List[float]            # 最近 N 次耗时（ms）
    duration_p50: Optional[float]
    duration_p95: Optional[float]
    status_timeline: List[Tuple[float, str]]  # (started_at, status) 倒序

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "window": self.window,
            "successes": self.successes,
            "failures": self.failures,
            "pass_rate": self.pass_rate,
            "duration_p50_ms": self.duration_p50,
            "duration_p95_ms": self.duration_p95,
            "durations_ms": self.durations_ms,
            "status_timeline": [
                {"at": t, "status": s} for t, s in self.status_timeline
            ],
        }


class TrendAnalyzer(Analyzer):
    name = "trend"

    def trend(
        self,
        store: Any,
        *,
        case_id: str,
        window: int = 50,
    ) -> CaseTrend:
        if not hasattr(store, "list_by_case"):
            raise TypeError("store must implement list_by_case")
        rows = store.list_by_case(case_id, limit=window)
        # 统一成 dict
        dicts = [r if isinstance(r, dict) else r.to_dict() for r in rows]
        dicts.sort(key=lambda r: r.get("started_at") or r.get("created_at") or 0, reverse=True)
        dicts = dicts[:window]

        successes = sum(1 for r in dicts if r.get("status") == "SUCCESS")
        failures = sum(
            1 for r in dicts if r.get("status") in ("FAILED", "TIMEOUT", "ERROR")
        )
        durations = [r.get("duration_ms") for r in dicts if r.get("duration_ms") is not None]
        p50 = _percentile(durations, 50)
        p95 = _percentile(durations, 95)
        timeline = [
            (r.get("started_at") or r.get("created_at") or 0, r.get("status", ""))
            for r in dicts
        ]
        return CaseTrend(
            case_id=case_id,
            window=len(dicts),
            successes=successes,
            failures=failures,
            pass_rate=round(successes / len(dicts), 4) if dicts else 0.0,
            durations_ms=[round(d, 3) for d in durations],
            duration_p50=round(p50, 3) if p50 is not None else None,
            duration_p95=round(p95, 3) if p95 is not None else None,
            status_timeline=timeline,
        )

    def run(
        self,
        store: Any,
        case_id: str,
        window: int = 50,
        **kwargs: Any,
    ) -> AnalyzerResult:
        t = self.trend(store, case_id=case_id, window=window)
        recs: List[str] = []
        if t.window >= 5 and t.pass_rate < 0.8:
            recs.append(
                f"case {t.case_id}: pass_rate={t.pass_rate:.2%}, 需要排查"
            )
        if t.duration_p95 is not None and t.duration_p50 is not None and t.duration_p50 > 0:
            slow = t.duration_p95 / t.duration_p50
            if slow > 3.0:
                recs.append(
                    f"case {t.case_id}: p95/p50={slow:.1f}x, 存在长尾"
                )
        return AnalyzerResult(
            name=self.name,
            summary=f"case {t.case_id}: {t.successes}/{t.window} pass, p50={t.duration_p50}",
            data=t.to_dict(),
            recommendations=recs,
        )


def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    k = (pct / 100.0) * (len(s) - 1)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return float(s[f])
    return float(s[f] + (s[c] - s[f]) * (k - f))
