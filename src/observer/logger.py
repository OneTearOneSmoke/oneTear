class LoggerObserver:
    def testcase_start(self, testcase, ctx):
        print(f"[TESTCASE START] {testcase.name} | context={ctx.vars}")

    def testcase_end(self, testcase, ctx):
        print(f"[TESTCASE END] {testcase.name}")

    def testcase_fail(self, testcase, ctx):
        print(f"[TESTCASE FAIL] {testcase.name}")

    def step_start(self, step, ctx):
        cmd_str = step.command.build("do", ctx.vars)
        print(f"[STEP START] {step.name} | CMD: {cmd_str}")

    def step_end(self, step, ctx):
        print(f"[STEP END] {step.name}")
        last_stdout = ctx.vars.get("last_stdout", "")
        last_stderr = ctx.vars.get("last_stderr", "")
        last_rc = ctx.vars.get("last_returncode", 0)
        if last_stdout:
            print(f"    STDOUT:\n{last_stdout.strip()}")
        if last_stderr:
            print(f"    STDERR:\n{last_stderr.strip()}")
        print(f"    Return code: {last_rc}")

    def step_fail(self, step, ctx):
        print(f"[STEP FAIL] {step.name}")
        last_stdout = ctx.vars.get("last_stdout", "")
        last_stderr = ctx.vars.get("last_stderr", "")
        last_rc = ctx.vars.get("last_returncode", 0)
        if last_stdout:
            print(f"    STDOUT:\n{last_stdout.strip()}")
        if last_stderr:
            print(f"    STDERR:\n{last_stderr.strip()}")
        print(f"    Return code: {last_rc}")
