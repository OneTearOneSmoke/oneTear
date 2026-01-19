import allure
import traceback
from contextlib import contextmanager
from observer.base import BaseObserver


class AllureObserver(BaseObserver):
    def __init__(self):
        # 用于维护 step 嵌套
        self._step_stack = []

    # =========================
    # Testcase level
    # =========================

    def testcase_start(self, testcase, context):
        """
        pytest 已经创建了 test case
        这里只做 metadata / description
        """
        allure.dynamic.title(testcase.name)

        desc = getattr(testcase, "description", None)
        if desc:
            allure.dynamic.description(desc)

        # context 作为 attachment（非常有用）
        allure.attach(
            str(context),
            name="context",
            attachment_type=allure.attachment_type.TEXT
        )

    def testcase_error(self, testcase, context, error):
        allure.attach(
            "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            name="exception",
            attachment_type=allure.attachment_type.TEXT
        )

    def testcase_end(self, testcase, context, success):
        # 不需要做任何事
        # pytest 会根据异常自动判定 PASS / FAIL
        pass

    # =========================
    # Step level
    # =========================

    def step_start(self, testcase, step, context):
        """
        每个 step 对应一个 allure.step
        """
        title = getattr(step, "name", "step")

        cm = allure.step(title)
        cm.__enter__()
        self._step_stack.append(cm)

        # 附加 step context（渲染后的）
        allure.attach(
            str(context),
            name=f"{title}-context",
            attachment_type=allure.attachment_type.TEXT
        )

    def step_end(self, testcase, step, context, result):
        """
        正常结束 step
        """
        # stdout / stderr / rc 非常关键
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        rc = result.get("rc")

        if stdout:
            allure.attach(
                stdout,
                name="stdout",
                attachment_type=allure.attachment_type.TEXT
            )

        if stderr:
            allure.attach(
                stderr,
                name="stderr",
                attachment_type=allure.attachment_type.TEXT
            )

        allure.attach(
            str(rc),
            name="return_code",
            attachment_type=allure.attachment_type.TEXT
        )

        cm = self._step_stack.pop()
        cm.__exit__(None, None, None)

    def step_error(self, testcase, step, context, error):
        """
        step 异常
        """
        allure.attach(
            "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            name="step_exception",
            attachment_type=allure.attachment_type.TEXT
        )

        cm = self._step_stack.pop()
        cm.__exit__(type(error), error, error.__traceback__)

    # =========================
    # Hook level（可选）
    # =========================

    def hook_start(self, testcase, hook, context):
        title = f"hook: {hook.name}"
        cm = allure.step(title)
        cm.__enter__()
        self._step_stack.append(cm)

    def hook_end(self, testcase, hook, context, result):
        cm = self._step_stack.pop()
        cm.__exit__(None, None, None)

    def hook_error(self, testcase, hook, context, error):
        allure.attach(
            str(error),
            name="hook_error",
            attachment_type=allure.attachment_type.TEXT
        )
        cm = self._step_stack.pop()
        cm.__exit__(type(error), error, error.__traceback__)
