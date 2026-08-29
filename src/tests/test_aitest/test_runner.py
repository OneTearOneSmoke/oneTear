import pytest

from aitest.assertors.basic import Eq, Contains
from aitest.commands.builtin import MakeTmp
from aitest.commands.python import PythonEval
from aitest.core.case import Case, CaseStep, CaseAssert
from aitest.core.registry import Registry
from aitest.core.runner import Runner


def _reg():
    reg = Registry()
    reg.command(instance=PythonEval())
    reg.command(instance=MakeTmp())
    reg.assertor(instance=Eq())
    reg.assertor(instance=Contains())
    return reg


def _assert(name, args):
    return CaseAssert(name=name, args=args)


def test_runner_python_eval_eq_passes():
    c = Case(
        id="t1",
        run=CaseStep(cmd="python.eval", args={"expr": "1+1"}),
        asserts=[_assert("eq", {"value": 2, "expect": 2})],
    )
    r = Runner(_reg()).run_case(c)
    assert r.ok, r.error


def test_runner_python_eval_eq_fails():
    c = Case(
        id="t2",
        run=CaseStep(cmd="python.eval", args={"expr": "1+1"}),
        asserts=[_assert("eq", {"value": 2, "expect": 3})],
    )
    r = Runner(_reg()).run_case(c)
    assert not r.ok
    assert "value=2 expect=3" in str(r.error)


def test_runner_template_rendering_in_args():
    c = Case(
        id="t3",
        params={"x": 5},
        run=CaseStep(cmd="python.eval", args={"expr": "{{ params.x }}*2"}),
        asserts=[_assert("eq", {"value": 10, "expect": 10})],
    )
    r = Runner(_reg()).run_case(c)
    assert r.ok, r.error


def test_runner_record_replay_on_failure(tmp_path):
    c = Case(
        id="rec.t1",
        run=CaseStep(cmd="python.eval", args={"expr": "1"}),
        asserts=[_assert("eq", {"value": 1, "expect": 2})],
        record={"on_failure": True},
    )
    c.record.dir = str(tmp_path / "replays")
    Runner(_reg()).run_case(c)
    files = list((tmp_path / "replays").glob("*.json"))
    assert files, "replay file should be created"


def test_runner_run_suite_serial():
    cases = [
        Case(
            id=f"t{i}",
            run=CaseStep(cmd="python.eval", args={"expr": str(i)}),
            asserts=[_assert("eq", {"value": i, "expect": i})],
        )
        for i in range(3)
    ]
    out = Runner(_reg()).run_suite(cases, concurrency=1)
    assert [r.case_id for r in out] == ["t0", "t1", "t2"]
    assert all(r.ok for r in out)
