from aitest.core.context import Context
from aitest.core.render import render, render_string


def test_render_simple_path():
    ctx = Context()
    ctx.params = {"name": "aitest"}
    assert render_string("hello {{ params.name }}", ctx) == "hello aitest"


def test_render_run_with_dotted_key():
    ctx = Context()
    ctx.run = {"python.eval": {"result": 42}}
    out = render_string("{{ run.python.eval.result }}", ctx)
    assert out == "42"


def test_render_with_filter():
    ctx = Context()
    ctx.params = {"xs": [3, 1, 2]}
    out = render_string("{{ params.xs | sorted | first }}", ctx)
    assert out == "1"


def test_render_object_attribute():
    from aitest.core.case import Case
    c = Case(id="abc", name="ABC")
    ctx = Context(case=c)
    out = render_string("{{ case.id }}/{{ case.name }}", ctx)
    assert out == "abc/ABC"


def test_render_passthrough_non_string():
    ctx = Context()
    ctx.params = {"a": 1, "b": [1, 2]}
    out = render({"x": "{{ params.a }}", "y": [1, "{{ params.b | first }}"]}, ctx)
    assert out == {"x": "1", "y": [1, "1"]}


def test_render_missing_key_returns_empty():
    ctx = Context()
    out = render_string("{{ params.nope }}", ctx)
    assert out == ""
