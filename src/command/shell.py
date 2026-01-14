import subprocess
from jinja2 import Environment, StrictUndefined

# =========================
# Jinja2 全局环境
# =========================
# - StrictUndefined：模板中引用未定义变量时直接抛异常（非常重要）
#   防止 silent failure（命令中变量未替换却悄悄执行）
# - autoescape=False：shell 命令不是 HTML，不需要转义
_env = Environment(
    undefined=StrictUndefined,
    autoescape=False
)


class ShellCommand:
    """
    ShellCommand 表示一个“可执行命令”的定义对象

    这是一个 *静态描述 + 动态渲染* 的命令模型：
    - cmd / redo_cmd / undo_cmd：命令模板（Jinja2 {{ }}）
    - build(...)：根据 context 渲染成最终 shell 命令
    - run(...)：真正执行 shell 命令
    """

    def __init__(self, name, cmd, redo_cmd="", undo_cmd="", description=""):
        """
        :param name: 命令名称（唯一标识，用于 cmd_ref）
        :param cmd: 主命令模板（do）
        :param redo_cmd: 重试命令模板（可选，默认等于 cmd）
        :param undo_cmd: 回滚命令模板（可选）
        :param description: 命令说明（用于日志 / Allure 展示）
        """
        self.name = name

        # =========================
        # 预编译 Jinja2 模板
        # =========================
        # 在加载阶段就把字符串编译为 Template
        # 好处：
        # - 运行时更快
        # - 提前暴露语法错误
        self.templates = {
            "do": _env.from_string(cmd),
            "redo": _env.from_string(redo_cmd or cmd),
            "undo": _env.from_string(undo_cmd) if undo_cmd else None,
        }

        self.description = description

    def build(self, action: str, context: dict) -> str:
        """
        根据 action + context 渲染最终可执行的 shell 命令字符串

        :param action:
            - "do"   : 正常执行
            - "redo" : 重试执行（Eventually / 重跑场景）
            - "undo" : 回滚（失败清理）
        :param context:
            执行上下文（testcase context + matrix 变量 + runtime 变量）

        :return:
            渲染完成的 shell 命令字符串
            如果该 action 没有定义模板，返回空字符串
        """
        tpl = self.templates.get(action)
        if not tpl:
            return ""

        # StrictUndefined 生效点：
        # 如果 context 缺少变量，这里会直接抛异常
        return tpl.render(**context)

    def run(self, cmd: str):
        """
        实际执行 shell 命令

        ⚠️ 注意：
        - 这里只负责“执行”，不做断言
        - 不做重试
        - 不关心 testcase / step 语义
        - engine 会负责 orchestration

        :param cmd: 已渲染完成的 shell 命令
        :return: 标准化的执行结果 dict
        """
        # 空命令直接视为 no-op
        if not cmd:
            return {
                "stdout": "",
                "stderr": "",
                "rc": 0,
            }

        # =========================
        # 使用 subprocess.run 执行
        # =========================
        # shell=True：
        #   - 允许使用 shell 特性（管道、重定向等）
        # capture_output=True：
        #   - 捕获 stdout / stderr
        # text=True：
        #   - 返回 str 而不是 bytes
        p = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )

        return {
            "stdout": p.stdout,
            "stderr": p.stderr,
            "rc": p.returncode,
        }
