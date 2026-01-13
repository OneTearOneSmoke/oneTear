from jinja2 import Environment, StrictUndefined, TemplateError
from command.base import Command


_jinja_env = Environment(
    undefined=StrictUndefined,   # 缺变量直接失败
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


class ShellCommand(Command):
    def __init__(self, name: str, cmd_template: str):
        super().__init__(name)
        self.cmd_template = cmd_template
        self._template = _jinja_env.from_string(cmd_template)

    def build_command(self, context: dict) -> str:
        """
        使用 Jinja2 + {{ }} 渲染 shell 命令
        """
        try:
            print("TEMPLATE:", self.cmd_template)
            print("CONTEXT:", context)
            return self._template.render(**context)
        except TemplateError as e:
            raise ValueError(
                f"[ShellCommand:{self.name}] render failed: {e}\n"
                f"template: {self.cmd_template}\n"
                f"context: {context}"
            )
