"""
Process Chaos
进程相关故障，例如 kill / restart
"""
import time
from chaos.base import Chaos

class KillProcess(Chaos):
    def __init__(self, cmd, recover_cmd="", duration=0):
        self.cmd = cmd
        self.recover_cmd = recover_cmd
        self.duration = duration

    def execute(self, context):
        print(f"[Chaos] inject: {self.cmd}")
        time.sleep(self.duration)
        if self.recover_cmd:
            print(f"[Chaos] recover: {self.recover_cmd}")

