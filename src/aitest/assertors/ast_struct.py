"""ast_struct —— 两段 Python 源码 AST 结构等价（忽略行号/列号）。"""
import ast

from ..core.errors import AssertFailure


class AstStruct:
    name = "ast_struct"

    def check(self, args, ctx):
        a = args.get("a", "")
        b = args.get("b", "")
        try:
            ta = ast.dump(ast.parse(a), annotate_fields=False, include_attributes=False)
            tb = ast.dump(ast.parse(b), annotate_fields=False, include_attributes=False)
        except SyntaxError as e:
            raise AssertFailure(self.name, f"syntax error: {e}")
        if ta != tb:
            raise AssertFailure(self.name, "AST not equal")
        return True
