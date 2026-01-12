"""
Contains 断言
检查输出是否包含期望文本
"""
from assertor.base import BaseAssert

class ContainsAssert(BaseAssert):
    def __init__(self, keywords):
        self.keywords = keywords if isinstance(keywords, list) else [keywords]

    def verify(self, context):
        last_output = context.get("last_output", "")
        for kw in self.keywords:
            if kw not in last_output:
                raise AssertionError(f"'{kw}' not found in output")
        print(f"[Assert] contains {self.keywords} OK")

