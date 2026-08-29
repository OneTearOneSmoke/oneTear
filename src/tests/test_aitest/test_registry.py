from aitest.core.registry import Registry


class Cmd:
    name = "demo.cmd"

    def run(self, args, ctx):
        return {"ok": True}


class Ass:
    name = "demo.ass"

    def check(self, args, ctx):
        return None


def test_register_via_decorator_and_instance():
    reg = Registry()
    reg.command(instance=Cmd())
    reg.assertor(instance=Ass())
    assert reg.get_command("demo.cmd").run(None, None)["ok"] is True
    assert reg.get_assertor("demo.ass") is not None


def test_register_via_string_decorator():
    reg = Registry()

    @reg.command("hello")
    class _C:
        def run(self, args, ctx):
            return {"hi": 1}

    assert reg.get_command("hello").run({}, None)["hi"] == 1


def test_get_missing_raises():
    reg = Registry()
    try:
        reg.get_command("nope")
    except KeyError as e:
        assert "nope" in str(e)
    else:
        raise AssertionError("expected KeyError")
