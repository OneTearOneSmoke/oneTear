"""Registry —— 命令/断言/观察者/Provider 的统一注册中心。"""
from typing import Any, Callable, Dict, List


class Registry:
    def __init__(self) -> None:
        self._commands: Dict[str, Any] = {}
        self._assertors: Dict[str, Any] = {}
        self._providers: Dict[str, Any] = {}
        self._observers: List[Any] = []

    # ---- commands ----
    def command(self, arg=None, *, name: str | None = None, instance: Any = None):
        if instance is not None:
            self._commands[getattr(instance, "name", type(instance).__name__)] = instance
            return instance
        if isinstance(arg, str):
            key = arg

            def deco(obj):
                self._commands[key] = obj() if isinstance(obj, type) else obj
                return obj

            return deco
        # @reg.command (no args)
        obj = arg
        key = name or getattr(obj, "name", getattr(obj, "__name__", str(obj)))
        self._commands[key] = obj() if isinstance(obj, type) else obj
        return obj

    def get_command(self, name: str) -> Any:
        if name not in self._commands:
            raise KeyError(f"command not registered: {name}")
        return self._commands[name]

    def list_commands(self) -> List[str]:
        return sorted(self._commands)

    # ---- assertors ----
    def assertor(self, arg=None, *, name: str | None = None, instance: Any = None):
        if instance is not None:
            self._assertors[getattr(instance, "name", type(instance).__name__)] = instance
            return instance
        if isinstance(arg, str):
            key = arg

            def deco(obj):
                self._assertors[key] = obj() if isinstance(obj, type) else obj
                return obj

            return deco
        obj = arg
        key = name or getattr(obj, "name", getattr(obj, "__name__", str(obj)))
        self._assertors[key] = obj() if isinstance(obj, type) else obj
        return obj

    def get_assertor(self, name: str) -> Any:
        if name not in self._assertors:
            raise KeyError(f"assertor not registered: {name}")
        return self._assertors[name]

    def list_assertors(self) -> List[str]:
        return sorted(self._assertors)

    # ---- providers ----
    def provider(self, arg=None, *, name: str | None = None, instance: Any = None):
        if instance is not None:
            self._providers[getattr(instance, "name", type(instance).__name__)] = instance
            return instance
        if isinstance(arg, str):
            key = arg

            def deco(obj):
                self._providers[key] = obj() if isinstance(obj, type) else obj
                return obj

            return deco
        obj = arg
        key = name or getattr(obj, "name", getattr(obj, "__name__", str(obj)))
        self._providers[key] = obj() if isinstance(obj, type) else obj
        return obj

    def get_provider(self, name: str) -> Any:
        if name not in self._providers:
            raise KeyError(f"provider not registered: {name}")
        return self._providers[name]

    def list_providers(self) -> List[str]:
        return sorted(self._providers)

    # ---- observers ----
    def observer(self, instance: Any) -> Any:
        self._observers.append(instance)
        return instance

    def observers(self) -> List[Any]:
        return list(self._observers)
