class Step:
    def __init__(self, name, command, asserter=None):
        self.name = name
        self.command = command
        self.asserter = asserter
