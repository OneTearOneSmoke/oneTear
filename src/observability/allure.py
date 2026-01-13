# observability/allure.py
import time

class AllureObserver:
    def __init__(self):
        try:
            import allure
            self.allure = allure
        except ImportError:
            self.allure = None

    # ========== testcase ==========
    def testcase_start(self, name):
        if not self.allure:
            return
        self.allure.dynamic.title(name)

    def testcase_end(self, name):
        pass

    def testcase_fail(self, name, err):
        if not self.allure:
            return
        self.allure.attach(
            str(err),
            name="error",
            attachment_type=self.allure.attachment_type.TEXT,
        )

    # ========== step ==========
    def step_start(self, name):
        if not self.allure:
            return
        self._step_ctx = self.allure.step(name)
        self._step_ctx.__enter__()

    def step_end(self, name, success, duration):
        if not self.allure:
            return
        self._step_ctx.__exit__(None, None, None)

    # ========== hook ==========
    def hook_start(self, phase, cmd):
        if not self.allure:
            return
        self.allure.attach(
            cmd,
            name=f"hook:{phase}",
            attachment_type=self.allure.attachment_type.TEXT,
        )

    def hook_end(self, phase, cmd):
        pass
