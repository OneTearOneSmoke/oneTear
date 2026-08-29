from aitest.assertors.basic import Contains, Eq, Ne, Regex, Truthy
from aitest.assertors.embedding import EmbeddingSim
from aitest.assertors.eventually import Eventually
from aitest.assertors.property import Property
from aitest.core.context import Context
from aitest.core.errors import AssertFailure
from aitest.core.registry import Registry


def test_eq():
    Eq().check({"value": 1, "expect": 1}, Context())
    try:
        Eq().check({"value": 1, "expect": 2}, Context())
    except AssertFailure:
        return
    raise AssertionError("should fail")


def test_ne():
    Ne().check({"value": 1, "expect": 2}, Context())
    Ne().check({"value": "a", "expect": "b"}, Context())


def test_contains_and_regex():
    Contains().check({"value": "abcdef", "substr": "cd"}, Context())
    Regex().check({"value": "abc 123", "pattern": r"\d+"}, Context())


def test_truthy():
    Truthy().check({"value": [1]}, Context())
    try:
        Truthy().check({"value": []}, Context())
    except AssertFailure:
        return
    raise AssertionError("should fail")


def test_embedding_sim_passes():
    EmbeddingSim().check(
        {"a": "today is good", "b": "today is great", "threshold": 0.1}, Context()
    )


def test_embedding_sim_fails():
    try:
        EmbeddingSim().check(
            {"a": "apple", "b": "completely unrelated xyz", "threshold": 0.9}, Context()
        )
    except AssertFailure:
        return
    raise AssertionError("should fail")


def test_property_check():
    Property().check({"expr": "1+1==2"}, Context())
    try:
        Property().check({"expr": "1+1==3"}, Context())
    except AssertFailure:
        return
    raise AssertionError("should fail")


def test_eventually_eq(monkeypatch):
    # 通过 monkeypatch time.sleep 加速
    import aitest.assertors.eventually as mod
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)
    Eventually().check(
        {"kind": "eq", "value": 1, "expect": 1, "timeout": 0.1, "interval": 0.01},
        Context(),
    )
