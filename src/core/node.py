from jinja2 import Template
class ExecutionNode:
    def __init__(self, name, executor, cmd_template, expect=None):
        self.name = name
        self.executor = executor
        self.cmd_template = cmd_template
        self.expect = expect or {}

    def run(self, context):
        cmd = self.executor.build(self.cmd_template, context)
        # 渲染 expect 中的 {{}} 变量
        rendered_expect = {}
        for k,v in self.expect.items():
            if isinstance(v, str):
                rendered_expect[k] = Template(v).render(**context)
            else:
                rendered_expect[k] = v
        return self.executor.run(cmd, context, expect=rendered_expect)
