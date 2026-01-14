from abc import ABC, abstractmethod

class CommandDefinition(ABC):
    def __init__(self, name, description=""):
        self.name = name
        self.description = description

    @abstractmethod
    def build(self, action: str, context: dict) -> str:
        """
        action: do | redo | undo
        """
        ...

    @abstractmethod
    def run(self, cmd: str):
        ...
