from chaos.base import Chaos
from core.runner import Runner
import time

class KillProcess(Chaos):
    def __init__(self, name, cmd, recover_cmd=None, duration=0):
        super().__init__(name)
        self.cmd = cmd
        self.recover_cmd = recover_cmd
        self.duration = duration

    def execute(self, context):
        Runner.run(self.cmd)
        if self.duration > 0:
            time.sleep(self.duration)

    def rollback(self, context):
        if self.recover_cmd:
            Runner.run(self.recover_cmd)
