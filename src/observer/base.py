from abc import ABC, abstractmethod


class BaseObserver(ABC):
    """
    Execution lifecycle observer

    所有 observer 必须实现这些方法
    ExecutionEngine 只依赖这一层抽象
    """

    # =========================
    # Testcase level
    # =========================

    @abstractmethod
    def testcase_start(self, testcase, context):
        """
        testcase 开始执行
        """

    @abstractmethod
    def testcase_error(self, testcase, context, error):
        """
        testcase 级别错误（未进入 step 或 step 冒泡）
        """

    @abstractmethod
    def testcase_end(self, testcase, context, success: bool):
        """
        testcase 执行结束（无论成功失败）
        """

    # =========================
    # Step level
    # =========================

    @abstractmethod
    def step_start(self, testcase, node, context):
        """
        step 开始执行
        """

    @abstractmethod
    def step_end(self, testcase, node, context, result: dict):
        """
        step 正常结束
        """

    @abstractmethod
    def step_error(self, testcase, node, context, error, result=None):
        """
        step 执行失败
        """
