from core.context import ExecutionContext
from command.shell import ShellCommand

class ExecutionEngine:
    def __init__(self, cmd_registry, observers=None, retry_defaults=None):
        self.cmd_registry = cmd_registry
        self.observers = observers or []
        self.retry_defaults = retry_defaults or {}

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
                rendered = step.asserter.render(ctx.vars)
                rendered.assert_result(
                    result,
                    retry_fn=lambda: self._redo_step(step, ctx),
                    retry_policy=self._resolve_retry_policy(step),
                )

            self.notify("step_end", step, ctx)

        except Exception as e:
            undo_cmd = step.command.build("undo", ctx.vars)
            step.command.run(undo_cmd)
            self.notify("step_fail", step, ctx)
            raise e

    def _redo_step(self, step, ctx):
        redo_cmd = step.command.build("redo", ctx.vars)
        result = step.command.run(redo_cmd)
        ctx.update(result)
        return result

    def _resolve_retry_policy(self, step):
        policy = dict(self.retry_defaults)
        policy.update(step.retry or {})
        return policy

    def _run_hooks(self, hooks, ctx):
        for h in hooks:
            if isinstance(h, str):
                cmd = ShellCommand("hook", h).build("do", ctx.vars)
                ShellCommand("hook", h).run(cmd)
                continue

            if isinstance(h, dict):
                cmd_ref = h.get("cmd_ref") or h.get("cmd")
                if not cmd_ref:
                    raise KeyError(f"hook missing cmd_ref/cmd: {h}")

                if "cmd_ref" in h:
                    cmd_def = self.cmd_registry.get(cmd_ref)
                    hook_cmd = cmd_def.build("do", ctx.vars)
                    cmd_def.run(hook_cmd)
                else:
                    hook_cmd = ShellCommand("hook", cmd_ref).build("do", ctx.vars)
                    ShellCommand("hook", cmd_ref).run(hook_cmd)
                continue

            raise TypeError(f"unsupported hook type: {type(h)}")
