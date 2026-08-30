"""TCM (Test Case Management) 子系统。

按 [`test-case-management-design.md`](../docs/ai-test/test-case-management-design.md)：

  - 用例模型：Case / Suite / Registry / Render / Step / Assert / Record
  - 生命周期：draft → active → deprecated → retired
  - 版本：semver + content_hash
  - Diff：meta + steps 两段对比
  - 矩阵展开 / 标签查询 / 路径加载

模块边界：只关心"用例是什么 / 怎么改 / 怎么查"，不掺 EXF 执行 / TRM 结果 / TMRM 资源。

对外 API 全部 dataclass，便于 Rust / Go 端 1:1 翻译。
"""

from .case import Case, CaseStep, CaseAssert, CaseRecord
from .suite import Suite
from .registry import Registry
from .render import render, render_string, resolve_args, resolve_string_value
from .lifecycle import (
    LifecycleStatus,
    IllegalTransition,
    transition,
    allowed_next,
    is_terminal as lifecycle_is_terminal,
    can_run as lifecycle_can_run,
)
from .version import (
    CaseVersion,
    content_hash,
    parse_semver,
    format_semver,
    bump_semver,
)
from .diff import CaseDiff, StepDiff, diff_cases, diff_suites, META_FIELDS, STEP_FIELDS

__all__ = [
    "Case", "CaseStep", "CaseAssert", "CaseRecord",
    "Suite", "Registry",
    "render", "render_string", "resolve_args", "resolve_string_value",
    "LifecycleStatus", "IllegalTransition",
    "transition", "allowed_next", "lifecycle_is_terminal", "lifecycle_can_run",
    "CaseVersion", "content_hash", "parse_semver", "format_semver", "bump_semver",
    "CaseDiff", "StepDiff", "diff_cases", "diff_suites", "META_FIELDS", "STEP_FIELDS",
]
