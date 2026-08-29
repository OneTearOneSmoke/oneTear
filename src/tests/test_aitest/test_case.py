from aitest.core.case import Case, CaseStep, CaseAssert, CaseRecord


def test_case_from_dict_minimal():
    c = Case.from_dict({"id": "x"})
    assert c.id == "x"
    assert c.name == "x"
    assert c.tags == []
    assert c.run is None
    assert c.asserts == []


def test_case_from_dict_full():
    d = {
        "id": "demo",
        "name": "Demo",
        "tags": ["t1", "t2"],
        "params": {"x": 1, "y": [1, 2]},
        "fixture": {
            "setup": [{"cmd": "builtin.make_tmp"}],
            "teardown": [{"cmd": "builtin.clean_tmp"}],
        },
        "run": {"cmd": "python.eval", "args": {"expr": "1+1"}},
        "asserts": {
            "eq": {"value": 2, "expect": 2},
            "contains": {"value": "abc", "substr": "b"},
        },
        "record": {"on_failure": True},
        "owner": "alice",
        "source": "human",
    }
    c = Case.from_dict(d, path="<mem>")
    assert c.fixture_setup[0].cmd == "builtin.make_tmp"
    assert c.fixture_teardown[0].cmd == "builtin.clean_tmp"
    assert c.run.cmd == "python.eval"
    assert [a.name for a in c.asserts] == ["eq", "contains"]
    assert c.record.on_failure is True
    assert c.owner == "alice"


def test_case_roundtrip():
    d = {
        "id": "demo",
        "run": {"cmd": "python.eval", "args": {"expr": "1"}},
        "asserts": {"eq": {"value": 1, "expect": 1}},
    }
    c = Case.from_dict(d)
    out = c.to_dict()
    assert out["id"] == "demo"
    assert out["run"]["cmd"] == "python.eval"
    assert out["asserts"][0]["eq"]["value"] == 1


def test_case_missing_id_raises():
    import pytest
    with pytest.raises(ValueError):
        Case.from_dict({})
