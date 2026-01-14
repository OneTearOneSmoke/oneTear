from typing import List, Dict

class Hooks:
    def __init__(self, before=None, after=None, on_fail=None):
        self.before: List[Dict] = before or []
        self.after: List[Dict] = after or []
        self.on_fail: List[Dict] = on_fail or []

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            before=cls._normalize(data.get("before")),
            after=cls._normalize(data.get("after")),
            on_fail=cls._normalize(data.get("on_fail")),
        )

    @staticmethod
    def _normalize(items):
        if not items:
            return []
        normalized = []
        for item in items:
            if isinstance(item, str):
                normalized.append({"cmd": item, "type": "shell"})
            else:
                normalized.append(item)
        return normalized
