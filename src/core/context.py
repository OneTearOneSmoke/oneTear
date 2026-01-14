class ExecutionContext:
    def __init__(self, vars: dict):
        self.vars = dict(vars)

    def update(self, result: dict):
        self.vars.update({
            "last_stdout": result["stdout"],
            "last_stderr": result["stderr"],
            "last_returncode": result["rc"],
        })
