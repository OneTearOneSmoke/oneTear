import allure
import traceback
from observer.base import BaseObserver

class AllureObserver(BaseObserver):
    def __init__(self):
        self._step_stack = []

    # =========================
    # Testcase level
    # =========================
    def testcase_start(self, testcase, context):
        allure.dynamic.title(testcase.name)
        desc = getattr(testcase, "description", None)
        if desc:
            allure.dynamic.description(desc)

        allure.attach(
            str(context),
            name="context",
            attachment_type=allure.attachment_type.TEXT
        )

    def testcase_error(self, testcase, context, error):
        allure.attach(
            "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            name="testcase_exception",
            attachment_type=allure.attachment_type.TEXT
        )

    def testcase_end(self, testcase, context, success):
        pass  # pytest 自动处理 PASS/FAIL

    # =========================
    # Step level
    # =========================
    def step_start(self, testcase, step, context, result=None):
        title = getattr(step, "name", "step")
        cm = allure.step(title)
        cm.__enter__()
        self._step_stack.append(cm)

        # 附加关键信息
        info = {
            "cmd_ref": getattr(step, "cmd_ref", getattr(step, "name", "")),
            "expect": getattr(step, "expect", {}),
            "context": context
        }
        allure.attach(
            str(info),
            name=f"{title}-info",
            attachment_type=allure.attachment_type.JSON
        )

    def step_end(self, testcase, step, context, result):
        # step 内 stdout/stderr/rc
        if result:
            stdout = result.get("stdout")
            stderr = result.get("stderr")
            rc = result.get("rc")

            if stdout:
                allure.attach(stdout, name="stdout", attachment_type=allure.attachment_type.TEXT)
            if stderr:
                allure.attach(stderr, name="stderr", attachment_type=allure.attachment_type.TEXT)
            if rc is not None:
                allure.attach(str(rc), name="return_code", attachment_type=allure.attachment_type.TEXT)

        # 关闭 step
        cm = self._step_stack.pop()
        cm.__exit__(None, None, None)

    def step_error(self, testcase, step, context, error, result=None):
        # 附加 step info
        info = {
            "cmd_ref": getattr(step, "cmd_ref", getattr(step, "name", "")),
            "expect": getattr(step, "expect", {}),
            "context": context
        }
        allure.attach(str(info), name=f"{getattr(step,'name','step')}-info", attachment_type=allure.attachment_type.JSON)

        # 附加 stdout/stderr/rc
        if result:
            stdout = result.get("stdout")
            stderr = result.get("stderr")
            rc = result.get("rc")
            if stdout:
                allure.attach(stdout, name="stdout", attachment_type=allure.attachment_type.TEXT)
            if stderr:
                allure.attach(stderr, name="stderr", attachment_type=allure.attachment_type.TEXT)
            if rc is not None:
                allure.attach(str(rc), name="return_code", attachment_type=allure.attachment_type.TEXT)

        # 异常信息
        allure.attach(
            "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            name="step_exception",
            attachment_type=allure.attachment_type.TEXT
        )

        cm = self._step_stack.pop()
        cm.__exit__(type(error), error, error.__traceback__)

    # =========================
    # Hook level
    # =========================
    def hook_start(self, testcase, hook, context, result=None):
        title = f"hook: {hook.name}"
        cm = allure.step(title)
        cm.__enter__()
        self._step_stack.append(cm)
        # 可以附加 context
        allure.attach(str(context), name=f"{title}-context", attachment_type=allure.attachment_type.TEXT)

    def hook_end(self, testcase, hook, context, result=None):
        # 附加 hook 执行结果
        if result:
            stdout = result.get("stdout")
            stderr = result.get("stderr")
            rc = result.get("rc")
            if stdout:
                allure.attach(stdout, name="stdout", attachment_type=allure.attachment_type.TEXT)
            if stderr:
                allure.attach(stderr, name="stderr", attachment_type=allure.attachment_type.TEXT)
            if rc is not None:
                allure.attach(str(rc), name="return_code", attachment_type=allure.attachment_type.TEXT)

        cm = self._step_stack.pop()
        cm.__exit__(None, None, None)

    def hook_error(self, testcase, hook, context, error, result=None):
        # 附加 context & result
        info = {"context": context}
        if result:
            info.update(result)
        allure.attach(str(info), name=f"{hook.name}-error-info", attachment_type=allure.attachment_type.JSON)

        allure.attach(
            "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            name="hook_exception",
            attachment_type=allure.attachment_type.TEXT
        )

        cm = self._step_stack.pop()
        cm.__exit__(type(error), error, error.__traceback__)
