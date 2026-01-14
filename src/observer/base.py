# observer/base.py
class BaseObserver:
    # ---------- TestCase ----------
    def testcase_start(self, testcase, ctx):
        pass

    def testcase_end(self, testcase, ctx):
        pass

    def testcase_fail(self, testcase, ctx):
        pass

    # ---------- Step ----------
    def step_start(self, step, ctx):
        pass

    def step_end(self, step, ctx):
        pass

    def step_fail(self, step, ctx):
        pass
