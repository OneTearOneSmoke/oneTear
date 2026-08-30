"""TRM (Test Report Management) 单测。"""
from __future__ import annotations
import os
import tempfile
from pathlib import Path
from typing import List

import pytest

from aitest.core.state import Status
from aitest.core.store import ResultStore
from aitest.trm.flaky import FlakyDetector, FlakyConfig
from aitest.trm.baseline import BaselineComparator, BaselineConfig
from aitest.trm.trend import TrendAnalyzer
from aitest.trm.analyzer import AnalyzerRegistry, AnalyzerResult


# ────────────────── Fixtures ──────────────────

@pytest.fixture
def store_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


@pytest.fixture
def store(store_path):
    s = ResultStore(store_path)
    yield s
    s.close()


def _seed_history(store: ResultStore, case_id: str, statuses: List[str], plan_id: str = "p1") -> None:
    """往 store 写一组历史结果（带时间戳递增）。

    task_id 包含 plan_id，避免不同 plan 重复主键冲突。
    """
    base = 1_000_000.0
    for i, s in enumerate(statuses):
        store.upsert(
            task_id=f"{plan_id}::{case_id}#{i}",
            case_id=case_id,
            case_version=1,
            case_name=case_id,
            plan_id=plan_id,
            plugin="mock",
            target_id="mock",
            status=s,
            attempt=1,
            started_at=base + i,
            finished_at=base + i + 0.1,
            duration_ms=10.0 + i,
            error_code=None if s == "SUCCESS" else "ASSERT_FAIL",
            error_message=None if s == "SUCCESS" else f"failed at {i}",
        )


# ────────────────── Flaky ──────────────────

class TestFlakyDetector:
    def test_detect_mixed_history_is_flaky(self, store):
        # 5 SUCCESS + 5 FAILED → 50% 失败 → flaky（默认 [0.05, 0.50] 包含 0.5）
        _seed_history(store, "ai.x", ["SUCCESS"] * 5 + ["FAILED"] * 5)
        det = FlakyDetector()
        flaky = det.detect(store, config=FlakyConfig(window=10))
        assert len(flaky) == 1
        f = flaky[0]
        assert f.case_id == "ai.x"
        assert f.failures == 5
        assert f.successes == 5
        assert f.is_flaky is True

    def test_all_pass_not_flaky(self, store):
        _seed_history(store, "ai.p", ["SUCCESS"] * 10)
        det = FlakyDetector()
        flaky = det.detect(store, config=FlakyConfig(window=10))
        assert flaky == []

    def test_all_fail_not_flaky(self, store):
        _seed_history(store, "ai.q", ["FAILED"] * 10)
        det = FlakyDetector()
        flaky = det.detect(store, config=FlakyConfig(window=10))
        assert flaky == []

    def test_low_fail_ratio_outside_band(self, store):
        # 1/20 = 5% → boundary included → flaky
        # 1/30 = 3.3% → outside lower band → not flaky
        statuses = ["SUCCESS"] * 29 + ["FAILED"]
        _seed_history(store, "ai.r", statuses)
        det = FlakyDetector()
        flaky = det.detect(store, config=FlakyConfig(window=30))
        assert flaky == []

    def test_plan_filter(self, store):
        _seed_history(store, "ai.s", ["SUCCESS", "FAILED"] * 3, plan_id="pA")
        _seed_history(store, "ai.t", ["SUCCESS", "FAILED"] * 3, plan_id="pB")
        det = FlakyDetector()
        flaky = det.detect(store, plan_id="pA", config=FlakyConfig(window=10))
        assert len(flaky) == 1
        assert flaky[0].case_id == "ai.s"

    def test_run_returns_analyzer_result(self, store):
        _seed_history(store, "ai.u", ["SUCCESS", "FAILED"] * 3)
        det = FlakyDetector()
        result = det.run(store)
        assert isinstance(result, AnalyzerResult)
        assert result.name == "flaky"
        assert "items" in result.data
        assert result.summary


# ────────────────── Baseline ──────────────────

class TestBaselineComparator:
    def test_new_failure(self, store):
        _seed_history(store, "ai.b", ["SUCCESS"], plan_id="base")
        _seed_history(store, "ai.b", ["FAILED"], plan_id="curr")
        comp = BaselineComparator()
        diffs = comp.compare(store, baseline_plan_id="base", current_plan_id="curr")
        kinds = {d.case_id: d.kind for d in diffs}
        assert kinds["ai.b"] == "NEW_FAILURE"

    def test_fixed(self, store):
        _seed_history(store, "ai.f", ["FAILED"], plan_id="base")
        _seed_history(store, "ai.f", ["SUCCESS"], plan_id="curr")
        comp = BaselineComparator()
        diffs = comp.compare(store, baseline_plan_id="base", current_plan_id="curr")
        kinds = {d.case_id: d.kind for d in diffs}
        assert kinds["ai.f"] == "FIXED"

    def test_regression(self, store):
        # 基线 FAILED + 当前 ERROR → 不同失败状态 → REGRESSION
        _seed_history(store, "ai.rg", ["FAILED"], plan_id="base")
        _seed_history(store, "ai.rg", ["ERROR"], plan_id="curr")
        comp = BaselineComparator()
        diffs = comp.compare(store, baseline_plan_id="base", current_plan_id="curr")
        kinds = {d.case_id: d.kind for d in diffs}
        assert kinds["ai.rg"] == "REGRESSION"

    def test_still_pass(self, store):
        _seed_history(store, "ai.sp", ["SUCCESS"], plan_id="base")
        _seed_history(store, "ai.sp", ["SUCCESS"], plan_id="curr")
        comp = BaselineComparator()
        diffs = comp.compare(store, baseline_plan_id="base", current_plan_id="curr")
        kinds = {d.case_id: d.kind for d in diffs}
        assert kinds["ai.sp"] == "STILL_PASS"

    def test_new_pass(self, store):
        # 基线没有，当前有 SUCCESS
        _seed_history(store, "ai.np", ["SUCCESS"], plan_id="curr")
        comp = BaselineComparator()
        diffs = comp.compare(store, baseline_plan_id="base", current_plan_id="curr")
        kinds = {d.case_id: d.kind for d in diffs}
        assert kinds["ai.np"] == "NEW_PASS"

    def test_run_counts(self, store):
        _seed_history(store, "ai.x1", ["SUCCESS"], plan_id="base")
        _seed_history(store, "ai.x1", ["FAILED"], plan_id="curr")
        _seed_history(store, "ai.x2", ["FAILED"], plan_id="base")
        _seed_history(store, "ai.x2", ["SUCCESS"], plan_id="curr")
        comp = BaselineComparator()
        result = comp.run(store, baseline_plan_id="base", current_plan_id="curr")
        counts = result.data["counts"]
        assert counts["NEW_FAILURE"] == 1
        assert counts["FIXED"] == 1


# ────────────────── Trend ──────────────────

class TestTrendAnalyzer:
    def test_trend_aggregates_pass_rate(self, store):
        _seed_history(store, "ai.t", ["SUCCESS"] * 7 + ["FAILED"] * 3)
        ana = TrendAnalyzer()
        t = ana.trend(store, case_id="ai.t", window=20)
        assert t.window == 10
        assert t.successes == 7
        assert t.failures == 3
        assert abs(t.pass_rate - 0.7) < 0.001

    def test_duration_percentiles(self, store):
        _seed_history(store, "ai.d", ["SUCCESS"] * 10)
        ana = TrendAnalyzer()
        t = ana.trend(store, case_id="ai.d", window=20)
        # 10..19 → p50 ≈ 14.5, p95 ≈ 18.55
        assert t.duration_p50 is not None
        assert t.duration_p95 is not None
        assert t.duration_p50 < t.duration_p95

    def test_status_timeline_ordered_desc(self, store):
        _seed_history(store, "ai.o", ["SUCCESS", "FAILED", "SUCCESS"])
        ana = TrendAnalyzer()
        t = ana.trend(store, case_id="ai.o", window=10)
        ts = [x[0] for x in t.status_timeline]
        assert ts == sorted(ts, reverse=True)

    def test_run_recommends_low_pass_rate(self, store):
        # 1 PASS + 9 FAILED = 10% 通过率（< 80%）→ 触发建议
        _seed_history(store, "ai.bad", ["SUCCESS"] + ["FAILED"] * 9)
        ana = TrendAnalyzer()
        result = ana.run(store, case_id="ai.bad", window=10)
        assert result.recommendations
        assert any("pass_rate" in r for r in result.recommendations)


# ────────────────── AnalyzerRegistry ──────────────────

class TestAnalyzerRegistry:
    def test_register_and_get(self):
        r = AnalyzerRegistry()
        r.register(FlakyDetector())
        r.register(TrendAnalyzer())
        r.register(BaselineComparator())
        assert set(r.names()) == {"flaky", "trend", "baseline"}
        assert r.get("flaky").name == "flaky"

    def test_duplicate_register_raises(self):
        r = AnalyzerRegistry()
        r.register(FlakyDetector())
        with pytest.raises(ValueError):
            r.register(FlakyDetector())
