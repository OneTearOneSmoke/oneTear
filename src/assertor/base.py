"""
断言基类
每个断言必须实现 verify(context)
"""
class BaseAssert:
    def verify(self, context):
        raise NotImplementedError("Must implement verify")
