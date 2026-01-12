"""
Result 对象
用于封装每个 Step / 测试用例的执行结果
包括输出、状态、错误信息
"""
class Result:
    def __init__(self, name, success=True, output=None, error=None):
        self.name = name
        self.success = success
        self.output = output
        self.error = error
