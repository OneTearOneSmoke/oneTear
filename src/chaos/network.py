"""
Network Chaos
网络隔离 / 延迟注入
"""
import time
from chaos.base import Chaos
from command.shell import ShellCommand

class NetworkPartition(Chaos):
    def __init__(self, cmd, recover_cmd, duration):
        self.cmd = cmd
        self.recover_cmd = recover_cmd
        self.duration = duration

    def execute(self, context):
        ShellCommand(self.cmd).execute(context)
        time.sleep(self.duration)
        ShellCommand(self.recover_cmd).execute(context)
