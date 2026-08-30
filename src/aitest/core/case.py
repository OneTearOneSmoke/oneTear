"""Backward-compat shim — 实现在 `aitest.tcm.case`。

历史 import:
    from aitest.core.case import Case, CaseStep, CaseAssert, CaseRecord
仍然可用；新代码请直接 `from aitest.tcm import Case, ...`。
"""
from ..tcm.case import Case, CaseStep, CaseAssert, CaseRecord

__all__ = ["Case", "CaseStep", "CaseAssert", "CaseRecord"]
