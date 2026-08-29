"""aitest 的统一异常体系。"""


class CaseFailure(Exception):
    """用例级别失败（断言失败 / 命令失败 / 其它）。"""

    def __init__(self, stage: str, message: str, *, cause: Exception | None = None):
        super().__init__(f"[{stage}] {message}")
        self.stage = stage
        self.cause = cause


class AssertFailure(CaseFailure):
    def __init__(self, name: str, message: str, *, cause: Exception | None = None):
        super().__init__(f"assert:{name}", message, cause=cause)
        self.assert_name = name


class CommandFailure(CaseFailure):
    def __init__(self, cmd: str, message: str, *, cause: Exception | None = None):
        super().__init__(f"cmd:{cmd}", message, cause=cause)
        self.cmd = cmd
