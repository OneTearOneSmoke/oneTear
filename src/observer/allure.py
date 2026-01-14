# observer/allure.py
import allure
from observer.base import BaseObserver

class AllureObserver(BaseObserver):
    def testcase_start(self, suite, ctx):
        pass  # pytest 侧 Allure 用 test name

    def step_start(self, step, ctx):
        allure.dynamic.title(ctx.step_id)
        self._step = step
        self._ctx = ctx
        self._step_ctx = allure.step(ctx.step_id)
        self._step_ctx.__enter__()

    def step_end(self, step, ctx):
        self._step_ctx.__exit__(None, None, None)

    def step_fail(self, step, ctx):
        self._step_ctx.__exit__(Exception, Exception("step failed"), None)
