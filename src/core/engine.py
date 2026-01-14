import time
from core.context import ExecutionContext
from command.shell import ShellCommand

class ExecutionEngine:
    def __init__(self, cmd_registry, observers=None):
        self.cmd_registry = cmd_registry
        self.observers = observers or []

    def notify(self, event, *args):
        for obs in self.observers:
            fn = getattr(obs, event, None)
            if fn:
                fn(*args)

    def run(self, testcase):
        for vars in testcase.expand():
            ctx = ExecutionContext(vars,testcase)
            self.notify("testcase_start", testcase, ctx)
            try:
                self._run_hooks(testcase.hooks.before, ctx)

                for step in testcase.steps:
                    self._run_step(step, ctx)

                self._run_hooks(testcase.hooks.after, ctx)
                self.notify("testcase_end", testcase, ctx)
            except Exception:
                self._run_hooks(testcase.hooks.on_fail, ctx)
                self.notify("testcase_fail", testcase, ctx)
                raise

    def _run_step(self, step, ctx):
        ctx.next_step(step.name)
        self.notify("step_start", step, ctx)
        try:
            cmd_str = step.command.build("do", ctx.vars)
            result = step.command.run(cmd_str)
            ctx.update(result)

            if step.asserter:
                step.asserter.render(ctx.vars).assert_result(result)

            self.notify("step_end", step, ctx)

        except Exception as e:
            undo_cmd = step.command.build("undo", ctx.vars)
            step.command.run(undo_cmd)
            self.notify("step_fail", step, ctx)
            raise e

    def _run_hooks(self, hooks, ctx):
        for h in hooks:
            cmd = ShellCommand("hook", h).build("do", ctx.vars)
            ShellCommand("hook", h).run(cmd)
