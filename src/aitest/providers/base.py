from typing import List, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def complete(self, prompt: str, **kwargs) -> str: ...

    def embed(self, texts: List[str]) -> List[List[float]]: ...
