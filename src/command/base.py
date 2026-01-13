# command/base.py
from abc import ABC, abstractmethod


class Command(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def build_command(self, context: dict):
        """
        返回 Runner 可执行的 command
        e.g. str | list
        """
        pass
