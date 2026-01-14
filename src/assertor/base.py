"""
断言基类
每个断言必须实现 verify(context)
"""
from abc import ABC, abstractmethod

class Asserter(ABC):
    @abstractmethod
    def render(self, context: dict):
        ...

    @abstractmethod
    def assert_result(self, result: dict):
        ...
