# core/context.py
class ExecutionContext:
    def __init__(self, vars: dict, testcase):
        self.vars = dict(vars)
        self.testcase = testcase
        self.testcase_id = self._build_testcase_id()

        self.step_index = 0
        self.step_id = None

    def _build_testcase_id(self):
        if not self.testcase.matrix:
            return self.testcase.name

        parts = [
            f"{k}={self.vars[k]}"
            for k in self.testcase.matrix.keys()
        ]
        return f"{self.testcase.name}[{','.join(parts)}]"

    def next_step(self, step_name):
        self.step_index += 1
        self.step_id = f"{self.testcase_id}::step-{self.step_index}:{step_name}"

    def update(self, result: dict):
        self.vars.update({
            "last_stdout": result["stdout"],
            "last_stderr": result["stderr"],
            "last_returncode": result["rc"],
        })
