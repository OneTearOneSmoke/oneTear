"""ast.diff —— 对比两段 Python 源码的 AST 是否等价（忽略行号/列号/属性）。"""
import ast

from ..core.errors import CommandFailure


class AstDiff:
    name = "ast.diff"

    def run(self, args, ctx):
        a = args.get("a", "")
        b = args.get("b", "")
        try:
            ta = ast.dump(ast.parse(a), annotate_fields=False, include_attributes=False)
            tb = ast.dump(ast.parse(b), annotate_fields=False, include_attributes=False)
        except SyntaxError as e:
            raise CommandFailure(self.name, f"syntax error: {e}")
        return {"equal": ta == tb, "a": ta, "b": tb}
