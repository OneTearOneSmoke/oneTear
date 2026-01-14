class MockCommand:
    def __init__(self, name):
        self.name = name

    def build(self, template, context):
        return f"mocked {self.name}"

    def run(self, cmd, context, expect=None):
        print(f"[MOCK RUN] {cmd} with context {context} expect {expect}")
        return {"stdout": "mocked output", "stderr": "", "rc": 0}
