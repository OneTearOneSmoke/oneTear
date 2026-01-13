# command/shell.py
from command.base import Command


class ShellCommand(Command):
    def __init__(self, name: str, cmd_template: str):
        super().__init__(name)
        self.cmd_template = cmd_template

    def build_command(self, context: dict):
        """
        使用 context 渲染 shell 命令
        """
        try:
            return self.cmd_template.format(**context)
        except KeyError as e:
            raise ValueError(
                f"[ShellCommand:{self.name}] missing param {e} "
                f"for command: {self.cmd_template}"
            )
