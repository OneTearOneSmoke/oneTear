"""
ShellCommand
通过执行 shell 命令实现原子操作
"""
from command.base import Command

class ShellCommand(Command):
    def __init__(self, cmd):
        self.cmd = cmd

    def execute(self, context):
        # 简化实现：打印命令，更新上下文
        print(f"[ShellCommand] execute: {self.cmd}")
        context["last_output"] = "Primary=node1"

