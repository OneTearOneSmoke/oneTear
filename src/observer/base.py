class BaseObserver:
    def testcase_start(self, testcase, context): pass
    def step_start(self, testcase, node, context): pass
    def step_end(self, testcase, node, context, result): pass
    def testcase_error(self, testcase, context, error): pass
    def testcase_end(self, testcase, context, success): pass
