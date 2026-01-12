"""
Execution Context
用于存储测试执行过程中的上下文信息
包括节点信息、环境变量、测试参数等
"""
class Context(dict):
    """执行上下文，可以存储步骤输出、矩阵参数等"""
    def update_context(self, key, value):
        self[key] = value

