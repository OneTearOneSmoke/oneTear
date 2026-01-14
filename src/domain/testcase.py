import itertools

class TestCase:
    def __init__(self, name, matrix, context, steps, hooks):
        self.name = name
        self.matrix = matrix
        self.context = context
        self.steps = steps
        self.hooks = hooks

    def expand(self):
        if not self.matrix:
            yield self.context
            return
        keys = self.matrix.keys()
        for values in itertools.product(*self.matrix.values()):
            ctx = dict(self.context)
            ctx.update(dict(zip(keys, values)))
            yield ctx
