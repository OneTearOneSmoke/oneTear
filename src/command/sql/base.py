from jinja2 import Environment, StrictUndefined

_env = Environment(undefined=StrictUndefined, autoescape=False)


class BaseSQLCommand:
    """
    SQL Command 的抽象基类

    负责：
    - SQL 模板渲染
    - 统一执行接口

    子类负责：
    - 具体数据库连接与执行逻辑
    """

    def __init__(self, name, sql, description=""):
        self.name = name
        self.template = _env.from_string(sql)
        self.description = description

    def build(self, context: dict) -> str:
        """
        使用 context 渲染 SQL
        """
        return self.template.render(**context)

    def run(self, sql: str, context: dict):
        """
        执行 SQL（子类必须实现）
        """
        raise NotImplementedError
