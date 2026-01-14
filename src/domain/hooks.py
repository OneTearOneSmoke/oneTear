class Hooks:
    def __init__(self, before=None, after=None, on_fail=None):
        self.before = before or []
        self.after = after or []
        self.on_fail = on_fail or []
