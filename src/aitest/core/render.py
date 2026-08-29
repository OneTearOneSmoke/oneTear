"""模板解析:
  - 纯模板 "{{ expr | f1 | f2 }}"   → 求值为原始对象（保留 list/dict/int）
  - 混合模板 "prefix-{{ expr }}-sfx" → 渲染为字符串
  - 普通字符串                     → 原样返回
"""
import re
from typing import Any, Callable, Dict

_TOK = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
_PURE = re.compile(r"^\s*\{\{\s*([^}]+?)\s*\}\}\s*$")

_FILTERS: Dict[str, Callable[[Any], Any]] = {
    "sorted": sorted,
    "len": len,
    "lower": lambda x: x.lower() if isinstance(x, str) else x,
    "upper": lambda x: x.upper() if isinstance(x, str) else x,
    "repr": repr,
    "str": str,
    "int": int,
    "float": float,
    "list": list,
    "set": set,
    "first": lambda x: x[0] if x else None,
    "last": lambda x: x[-1] if x else None,
}


def _lookup(ctx: Any, path: str) -> Any:
    if isinstance(ctx, dict) and path in ctx:
        return ctx[path]
    parts = path.split(".")
    node = ctx
    i = 0
    while i < len(parts):
        if not isinstance(node, dict):
            node = getattr(node, parts[i], "")
            i += 1
            continue
        matched = False
        for j in range(len(parts), i, -1):
            key = ".".join(parts[i:j])
            if key in node:
                node = node[key]
                i = j
                matched = True
                break
        if not matched:
            node = node.get(parts[i], "")
            i += 1
    if callable(node):
        try:
            node = node()
        except Exception:  # noqa: BLE001
            node = ""
    return node


def _apply_filters(val: Any, fns: list[str]) -> Any:
    for f in fns:
        fn = _FILTERS.get(f)
        if fn:
            try:
                val = fn(val)
            except Exception:  # noqa: BLE001
                val = ""
    return val


def resolve_string_value(s: str, ctx: Any) -> Any:
    """字符串 → 对象/字符串。

    纯模板返回原始对象；混合模板/普通字符串返回字符串。
    """
    m = _PURE.match(s)
    if m:
        expr = m.group(1).strip()
        if "|" in expr:
            path, *fns = [x.strip() for x in expr.split("|")]
        else:
            path, fns = expr, []
        val = _lookup(ctx, path)
        val = _apply_filters(val, fns)
        return val
    if "{{" in s:
        return _render_mixed(s, ctx)
    return s


def _render_mixed(s: str, ctx: Any) -> str:
    def repl(m):
        expr = m.group(1).strip()
        if "|" in expr:
            path, *fns = [x.strip() for x in expr.split("|")]
        else:
            path, fns = expr, []
        val = _lookup(ctx, path)
        val = _apply_filters(val, fns)
        return "" if val is None else str(val)
    return _TOK.sub(repl, s)


def render(obj: Any, ctx: Any) -> Any:
    """向后兼容: 字符串全部按混合模板渲染（输出字符串）。

    新代码请用 resolve_args。
    """
    if isinstance(obj, str):
        if "{{" in obj:
            return _render_mixed(obj, ctx)
        return obj
    if isinstance(obj, dict):
        return {k: render(v, ctx) for k, v in obj.items()}
    if isinstance(obj, list):
        return [render(v, ctx) for v in obj]
    if isinstance(obj, tuple):
        return tuple(render(v, ctx) for v in obj)
    return obj


def resolve_args(args: Any, ctx: Any) -> Any:
    """递归解析 args: 纯模板 → 对象；混合模板/普通 → 字符串；其它原样。"""
    if isinstance(args, str):
        return resolve_string_value(args, ctx)
    if isinstance(args, dict):
        return {k: resolve_args(v, ctx) for k, v in args.items()}
    if isinstance(args, list):
        return [resolve_args(v, ctx) for v in args]
    if isinstance(args, tuple):
        return tuple(resolve_args(v, ctx) for v in args)
    return args

# 向后兼容别名
render_string = _render_mixed
