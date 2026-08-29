"""aitest: AI 时代的极简测试框架与用例管理。

设计要点：极小内核 + 强扩展点。
- 内核: Case / Suite / Registry / Runner / Loader
- 扩展点: commands / assertors / observers / providers
- 用例即数据: YAML/JSON，可进 git，可被 LLM 读写
"""
from .core.case import Case, CaseStep, CaseAssert, CaseRecord
from .core.suite import Suite
from .core.registry import Registry
from .core.runner import Runner
from .core.context import Context
from .core.result import Result

__all__ = [
    "Case", "CaseStep", "CaseAssert", "CaseRecord",
    "Suite", "Registry", "Runner", "Context", "Result",
]
__version__ = "0.1.0"
