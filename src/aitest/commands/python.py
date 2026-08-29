"""python.eval —— 执行 Python 表达式或函数调用（信任环境，不做沙箱）。"""
import importlib

from ..core.errors import CommandFailure


class PythonEval:
    name = "python.eval"

    def run(self, args, ctx):
        if "expr" in args:
            try:
                return {"result": eval(args["expr"], {"__builtins__": __builtins__})}
            except Exception as e:  # noqa: BLE001
                raise CommandFailure(self.name, f"expr failed: {e}")
        if "call" in args:
            target = args["call"]
            if "import" in args:
                mod = importlib.import_module(args["import"])
                fn = mod
                for p in target.split("."):
                    fn = getattr(fn, p)
            else:
                fn = eval(target, {"__builtins__": __builtins__})
            w = args.get("with")
            try:
                return {"result": fn(w)}
            except Exception as e:  # noqa: BLE001
                raise CommandFailure(self.name, f"call failed: {e}")
        raise CommandFailure(self.name, "need 'expr' or ('call' + optional 'import'/'with')")
