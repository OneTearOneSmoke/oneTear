from abc import ABC, abstractmethod

class Chaos(ABC):
    """故障注入基类"""

    def __init__(self, name):
        self.name = name

    @abstractmethod
    def execute(self, context):
        pass

    def rollback(self, context):
        """可选回滚动作"""
        pass
