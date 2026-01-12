"""
Command 抽象类
每个命令都必须继承此类并实现 execute 方法
"""
class Command:
    def execute(self, context):
        """
        执行命令逻辑
        :param context: 执行上下文
        """
        raise NotImplementedError("Command must implement execute")
