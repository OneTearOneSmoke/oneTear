"""
Chaos 抽象类
每个故障注入命令必须继承此类
"""
class Chaos:
    def execute(self, context):
        """
        注入故障
        :param context: 执行上下文
        """
        raise NotImplementedError("Chaos must implement execute")
