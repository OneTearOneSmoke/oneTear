# core/registry.py
from command.shell import ShellCommand
from chaos.process import KillProcess
from dsl.loader import load_commands, load_chaos

class Registry:
    """命令和故障注册表"""

    def __init__(self, cmd_path="conf/commands.yaml", chaos_path="conf/chaos.yaml"):
        self.registry = {}
        self._load_commands(cmd_path)
        self._load_chaos(chaos_path)

    def _load_commands(self, path):
        for cmd_conf in load_commands(path):
            self.registry[cmd_conf["name"]] = ShellCommand(cmd_conf["cmd"])

    def _load_chaos(self, path):
        for chaos_conf in load_chaos(path):
            self.registry[chaos_conf["name"]] = KillProcess(
                chaos_conf["cmd"],
                chaos_conf.get("recover_cmd", ""),
                chaos_conf.get("duration", 0)
            )

    def get(self, name):
        return self.registry.get(name)

    def keys(self):
        return list(self.registry.keys())

    def validate_testcase(self, testcase):
        """校验 testcase 中所有 step 的 cmd_ref 是否在 registry 中"""
        steps = testcase.get("steps", [])
        for step in steps:
            step_name = step.get("name")
            cmd_ref = step.get("cmd_ref", step_name)
            if cmd_ref not in self.registry:
                raise ValueError(
                    f"[Registry Error] Step '{step_name}' 的命令/故障 '{cmd_ref}' 没有在 registry 中注册. "
                    f"当前可用命令: {self.keys()}"
                )
