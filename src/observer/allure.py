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

        # context 作为 attachment
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
        pass  # pytest 会自动判定 PASS/FAIL

    # =========================
    # Step level
    # =========================
    def step_start(self, testcase, step, context, result=None):
        title = getattr(step, "name", "step")
        cm = allure.step(title)
        cm.__enter__()
        self._step_stack.append(cm)

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
        if result:
            self._attach_step_result(result)
        cm = self._step_stack.pop()
        cm.__exit__(None, None, None)

    def step_error(self, testcase, step, context, error, result=None):
        # 附加 step 信息
        info = {
            "cmd_ref": getattr(step, "cmd_ref", getattr(step, "name", "")),
            "expect": getattr(step, "expect", {}),
            "context": context
        }
        allure.attach(str(info), name=f"{getattr(step,'name','step')}-info", attachment_type=allure.attachment_type.JSON)

        # stdout/stderr/rc
        if result:
            self._attach_step_result(result)

        # 异常信息
        allure.attach(
            "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            name="step_exception",
            attachment_type=allure.attachment_type.TEXT
        )

        cm = self._step_stack.pop()
        cm.__exit__(type(error), error, error.__traceback__)

    def _attach_step_result(self, result):
        stdout = result.get("stdout")
        stderr = result.get("stderr")
        rc = result.get("rc")
        if stdout:
            allure.attach(stdout, name="stdout", attachment_type=allure.attachment_type.TEXT)
        if stderr:
            allure.attach(stderr, name="stderr", attachment_type=allure.attachment_type.TEXT)
        if rc is not None:
            allure.attach(str(rc), name="return_code", attachment_type=allure.attachment_type.TEXT)

    # =========================
    # Hook level
    # =========================
    def hook_start(self, testcase, hook, context, result=None):
        title = f"hook: {hook.name}"
        cm = allure.step(title)
        cm.__enter__()
        self._step_stack.append(cm)
        allure.attach(str(context), name=f"{title}-context", attachment_type=allure.attachment_type.TEXT)

    def hook_end(self, testcase, hook, context, result=None):
        if result:
            self._attach_step_result(result)
        cm = self._step_stack.pop()
        cm.__exit__(None, None, None)

    def hook_error(self, testcase, hook, context, error, result=None):
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
