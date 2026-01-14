import itertools
from domain.hooks import Hooks
from core.node import ExecutionNode

class TestCase:
    def __init__(self, name, matrix=None, context=None, steps=None, hooks: Hooks=None):
        self.name = name
        self.matrix = matrix or {}
        self.context = context or {}
        self.steps = steps or []
        self.hooks = hooks or Hooks()

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            name=data["name"],
            matrix=data.get("matrix"),
            context=data.get("context"),
            steps=data.get("steps"),
            hooks=Hooks.from_dict(data.get("hooks", {}))
        )

    def expand(self):
        if not self.matrix:
            yield dict(self.context)
            return
        keys = list(self.matrix.keys())
        for values in itertools.product(*self.matrix.values()):
            ctx = dict(self.context)
            ctx.update(dict(zip(keys, values)))
            yield ctx

    def get_nodes(self, command_registry):
        nodes = []
        for hook in self.hooks.before:
            cmd_str = hook.get("cmd")
            cmd_type = hook.get("type","shell")
            executor = command_registry.get("create_file")
            nodes.append(ExecutionNode(f"hook_before_{cmd_str}", executor, cmd_str))
        for step in self.steps:
            cmd_name = step.get("cmd_ref")
            executor = command_registry.get(cmd_name)
            nodes.append(ExecutionNode(step.get("name"), executor, cmd_name, expect=step.get("expect")))
        for hook in self.hooks.after:
            cmd_str = hook.get("cmd")
            executor = command_registry.get("create_file")
            nodes.append(ExecutionNode(f"hook_after_{cmd_str}", executor, cmd_str))
        for hook in self.hooks.on_fail:
            cmd_str = hook.get("cmd")
            executor = command_registry.get("create_file")
            nodes.append(ExecutionNode(f"hook_onfail_{cmd_str}", executor, cmd_str))
        return nodes
