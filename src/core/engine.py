class ExecutionEngine:
    def __init__(self, observers=None, command_registry=None):
        self.observers = observers or []
        self.command_registry = command_registry

    def run_testcase(self, testcase, context):
        ctx = dict(context)
        failed = False
        try:
            self._notify("testcase_start", testcase, ctx)
            nodes = testcase.get_nodes(self.command_registry)
            for node in nodes:
                self._notify("step_start", testcase, node, ctx)
                result = node.run(ctx)
                ctx["last_stdout"] = result["stdout"]
                ctx["last_stderr"] = result["stderr"]
                ctx["last_rc"] = result["rc"]
                self._notify("step_end", testcase, node, ctx, result)
        except Exception as e:
            failed = True
            self._notify("testcase_error", testcase, ctx, e)
            # on_fail hooks
            for node in nodes:
                if node.name.startswith("hook_onfail"):
                    self._notify("step_start", testcase, node, ctx)
                    node.run(ctx)
                    self._notify("step_end", testcase, node, ctx, {"stdout":"", "stderr":"", "rc":-1})
        finally:
            self._notify("testcase_end", testcase, ctx, not failed)

    def _notify(self, event, *args, **kwargs):
        for obs in self.observers:
            fn = getattr(obs, event, None)
            if callable(fn):
                try:
                    fn(*args, **kwargs)
                except Exception as e:
                    print(f"[ObserverError] {obs.__class__.__name__}.{event}: {e}")
