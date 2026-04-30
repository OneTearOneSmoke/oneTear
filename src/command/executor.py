from abc import ABC, abstractmethod


class CommandExecutor(ABC):
    @abstractmethod
    def build(self, action: str, context: dict) -> str:
        """
        Render command string for the given action and context.
        """

    @abstractmethod
    def run(self, cmd: str):
        """
        Execute a rendered command and return normalized result dict.
        """
