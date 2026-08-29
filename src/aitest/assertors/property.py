"""property —— 任意 Python 布尔表达式（应幂等 / 不变式）。"""
from ..core.errors import AssertFailure


class Property:
    name = "property"

    def check(self, args, ctx):
        expr = args.get("expr", "")
        env = {"__builtins__": __builtins__, "ctx": ctx, "params": ctx.params, "run": ctx.run}
        try:
            ok = bool(eval(expr, env))
        except Exception as e:  # noqa: BLE001
            raise AssertFailure(self.name, f"property eval error: {e}")
        if not ok:
            raise AssertFailure(self.name, f"property not satisfied: {expr}")
        return True
