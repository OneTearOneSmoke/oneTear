"""TCM (Test Case Management) 单测 —— 新增的 lifecycle / version / diff。"""
from __future__ import annotations
import copy
import pytest

from aitest.tcm.case import Case, CaseStep, CaseAssert
from aitest.tcm.lifecycle import (
    LifecycleStatus,
    IllegalTransition,
    transition,
    allowed_next,
    is_terminal,
    can_run,
)
from aitest.tcm.version import (
    CaseVersion,
    content_hash,
    parse_semver,
    format_semver,
    bump_semver,
)
from aitest.tcm.diff import diff_cases, diff_suites


# ──────────── Lifecycle ────────────

class TestLifecycle:
    def test_terminal_is_retired(self):
        assert is_terminal(LifecycleStatus.RETIRED)
        assert not is_terminal(LifecycleStatus.ACTIVE)

    def test_can_run_active_and_deprecated(self):
        assert can_run(LifecycleStatus.ACTIVE)
        assert can_run(LifecycleStatus.DEPRECATED)
        assert not can_run(LifecycleStatus.DRAFT)
        assert not can_run(LifecycleStatus.RETIRED)

    def test_allowed_next_from_draft(self):
        allowed = {s for s in allowed_next(LifecycleStatus.DRAFT)}
        assert allowed == {LifecycleStatus.ACTIVE, LifecycleStatus.RETIRED}

    def test_retired_is_terminal_no_transition(self):
        assert allowed_next(LifecycleStatus.RETIRED) == []

    def test_legal_transition(self):
        assert transition(LifecycleStatus.DRAFT, LifecycleStatus.ACTIVE) == LifecycleStatus.ACTIVE
        assert transition(LifecycleStatus.ACTIVE, LifecycleStatus.DEPRECATED) == LifecycleStatus.DEPRECATED
        assert transition(LifecycleStatus.DEPRECATED, LifecycleStatus.ACTIVE) == LifecycleStatus.ACTIVE
        assert transition(LifecycleStatus.DEPRECATED, LifecycleStatus.RETIRED) == LifecycleStatus.RETIRED

    def test_illegal_transition_raises(self):
        with pytest.raises(IllegalTransition):
            transition(LifecycleStatus.DRAFT, LifecycleStatus.DEPRECATED)
        with pytest.raises(IllegalTransition):
            transition(LifecycleStatus.RETIRED, LifecycleStatus.ACTIVE)

    def test_same_state_no_op(self):
        assert transition(LifecycleStatus.ACTIVE, LifecycleStatus.ACTIVE) == LifecycleStatus.ACTIVE


# ──────────── Version ────────────

class TestVersion:
    def test_parse_format(self):
        assert parse_semver("1.2.3") == (1, 2, 3)
        assert format_semver((1, 2, 3)) == "1.2.3"

    def test_parse_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_semver("1.2")
        with pytest.raises(ValueError):
            parse_semver("v1.2.3")

    def test_bump(self):
        assert bump_semver("1.2.3", "patch") == "1.2.4"
        assert bump_semver("1.2.3", "minor") == "1.3.0"
        assert bump_semver("1.2.3", "major") == "2.0.0"

    def test_content_hash_stable(self):
        d = {
            "id": "ai.x",
            "name": "x",
            "tags": ["smoke"],
            "run": {"cmd": "shell.run", "args": {"cmd": "echo hi"}},
            "path": "/tmp/whatever.yaml",  # 应被剔除
            "created_at": 1234567890,        # 应被剔除
        }
        h1 = content_hash(d)
        h2 = content_hash(d)
        assert h1 == h2
        assert len(h1) == 12

    def test_content_hash_changes_with_content(self):
        d1 = {"id": "ai.x", "run": {"cmd": "shell.run", "args": {"cmd": "echo hi"}}}
        d2 = {"id": "ai.x", "run": {"cmd": "shell.run", "args": {"cmd": "echo bye"}}}
        assert content_hash(d1) != content_hash(d2)

    def test_content_hash_ignores_path(self):
        d1 = {"id": "ai.x", "run": None, "path": "/a.yaml"}
        d2 = {"id": "ai.x", "run": None, "path": "/b.yaml"}
        assert content_hash(d1) == content_hash(d2)

    def test_case_version_str(self):
        v = CaseVersion(semver="1.0.0", content_hash="abc123def456")
        assert str(v) == "1.0.0+abc123def456"
        v2 = CaseVersion(semver="2.0.0")
        assert str(v2) == "2.0.0"


# ──────────── Diff ────────────

def _case(cid: str, **kwargs) -> Case:
    """构造最小用例用于 diff。"""
    base = {
        "id": cid,
        "name": cid,
        "tags": ["smoke"],
        "params": {},
        "run": {"cmd": "shell.run", "args": {"cmd": "echo hi"}},
        "asserts": [{"contains": "hi"}],
    }
    base.update(kwargs)
    return Case.from_dict(base)


class TestDiff:
    def test_identical_cases(self):
        a = _case("ai.x")
        b = _case("ai.x")
        d = diff_cases(a, b)
        assert d.identical
        assert d.meta == {}
        assert d.steps == []

    def test_meta_field_change(self):
        a = _case("ai.x", tags=["smoke"])
        b = _case("ai.x", tags=["smoke", "fast"])
        d = diff_cases(a, b)
        assert not d.identical
        assert "tags" in d.meta
        assert d.meta["tags"] == (["smoke"], ["smoke", "fast"])

    def test_step_field_change(self):
        a = _case("ai.x", run={"cmd": "shell.run", "args": {"cmd": "echo hi"}})
        b = _case("ai.x", run={"cmd": "shell.run", "args": {"cmd": "echo bye"}})
        d = diff_cases(a, b)
        assert not d.identical
        assert any(s.field == "run" and s.kind == "changed" for s in d.steps)

    def test_assert_added(self):
        a = _case("ai.x", asserts=[{"contains": "hi"}])
        b = _case("ai.x", asserts=[{"contains": "hi"}, {"len": 10}])
        d = diff_cases(a, b)
        assert not d.identical
        assert any(s.field == "asserts" for s in d.steps)

    def test_case_id_mismatch_raises(self):
        a = _case("ai.x")
        b = _case("ai.y")
        with pytest.raises(ValueError):
            diff_cases(a, b)

    def test_suite_diff_added(self):
        from aitest.tcm.suite import Suite
        sa = Suite(cases=[_case("ai.x")])
        sb = Suite(cases=[_case("ai.x"), _case("ai.y")])
        diffs = diff_suites(sa, sb)
        ids = {d.case_id: d for d in diffs}
        assert "ai.x" in ids
        assert "ai.y" in ids
        assert any(s.kind == "added" for s in ids["ai.y"].steps)

    def test_suite_diff_removed(self):
        from aitest.tcm.suite import Suite
        sa = Suite(cases=[_case("ai.x"), _case("ai.y")])
        sb = Suite(cases=[_case("ai.x")])
        diffs = diff_suites(sa, sb)
        ids = {d.case_id: d for d in diffs}
        assert any(s.kind == "removed" for s in ids["ai.y"].steps)

    def test_diff_to_dict_serializable(self):
        a = _case("ai.x")
        b = _case("ai.x", tags=["fast"])
        d = diff_cases(a, b)
        out = d.to_dict()
        assert out["case_id"] == "ai.x"
        assert out["identical"] is False
        assert isinstance(out["meta"], list)
        assert isinstance(out["steps"], list)


# ──────────── Backward compat ────────────

class TestBackwardCompat:
    """老的 core.case / core.suite 仍可用。"""
    def test_old_imports_work(self):
        from aitest.core.case import Case as OldCase
        from aitest.core.suite import Suite as OldSuite
        from aitest.core.registry import Registry as OldRegistry
        from aitest.core.render import render as old_render
        from aitest.tcm.case import Case as NewCase
        assert OldCase is NewCase
        s = OldSuite()
        s.add(NewCase.from_dict({"id": "x", "run": {"cmd": "shell.run", "args": {}}}))
        assert len(s) == 1
        assert OldRegistry is not None
        assert callable(old_render)
