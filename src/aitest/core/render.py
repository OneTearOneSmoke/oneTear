"""Backward-compat shim — 实现在 `aitest.tcm.render`."""
from ..tcm.render import (
    render,
    render_string,
    resolve_args,
    resolve_string_value,
)

__all__ = ["render", "render_string", "resolve_args", "resolve_string_value"]
