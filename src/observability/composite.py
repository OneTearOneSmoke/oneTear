# observability/composite.py
class CompositeObserver:
    def __init__(self, *observers):
        self._observers = observers

    def _safe_call(self, method, *args):
        for obs in self._observers:
            fn = getattr(obs, method, None)
            if callable(fn):
                try:
                    fn(*args)
                except Exception:
                    pass  # Observer 永远不能影响执行流程

    def testcase_start(self, name):
        self._safe_call("testcase_start", name)

    def testcase_end(self, name):
        self._safe_call("testcase_end", name)

    def testcase_fail(self, name, err):
        self._safe_call("testcase_fail", name, err)

    def step_start(self, name):
        self._safe_call("step_start", name)

    def step_end(self, name, success, duration):
        self._safe_call("step_end", name, success, duration)

    def hook_start(self, phase, cmd):
        self._safe_call("hook_start", phase, cmd)

    def hook_end(self, phase, cmd):
        self._safe_call("hook_end", phase, cmd)
