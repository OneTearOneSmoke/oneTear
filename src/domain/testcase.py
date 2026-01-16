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

        # ---------- before hooks ----------
        for i, hook in enumerate(self.hooks.before):
            cmd_name = hook["cmd_ref"]
            executor = command_registry.get(cmd_name)
            nodes.append(
                ExecutionNode(
                    name=f"hook_before_{cmd_name}_{i}",
                    executor=executor,
                    cmd_template=cmd_name
                )
            )

        # ---------- steps ----------
        for step in self.steps:
            cmd_name = step["cmd_ref"]
            executor = command_registry.get(cmd_name)
            nodes.append(
                ExecutionNode(
                    name=step["name"],
                    executor=executor,
                    cmd_template=cmd_name,
                    expect=step.get("expect")
                )
            )

        # ---------- after hooks ----------
        for i, hook in enumerate(self.hooks.after):
            cmd_name = hook["cmd_ref"]
            executor = command_registry.get(cmd_name)
            nodes.append(
                ExecutionNode(
                    name=f"hook_after_{cmd_name}_{i}",
                    executor=executor,
                    cmd_template=cmd_name
                )
            )

        # ---------- on_fail hooks ----------
        for i, hook in enumerate(self.hooks.on_fail):
            cmd_name = hook["cmd_ref"]
            executor = command_registry.get(cmd_name)
            nodes.append(
                ExecutionNode(
                    name=f"hook_onfail_{cmd_name}_{i}",
                    executor=executor,
                    cmd_template=cmd_name
                )
            )

        return nodes
