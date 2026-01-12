#!/usr/bin/env python3
import os

ROOT_DIR = "src"

DIRS = [
    "core",
    "command",
    "chaos",
    "dsl",
    "assertor",
    "observability",
    "cases",
    "conf",
]

# 基础文件模板，带详细注释
FILES = {
    # ---- 核心引擎 ----
    "core/engine.py": '''"""
Execution Engine
负责调度测试用例、步骤（Step）和故障（Chaos），并触发断言。
支持 DAG / 序列执行。
"""
class ExecutionEngine:
    def __init__(self, registry, observer):
        """
        初始化执行引擎
        :param registry: 命令/故障注册表
        :param observer: 观察者，用于 Allure / Trace / Metric
        """
        self.registry = registry
        self.observer = observer

    def run_testcase(self, testcase, context):
        """执行单个测试用例"""
        self.observer.testcase_start(testcase)
        try:
            for step in testcase.steps:
                self.run_step(step, context)
            if hasattr(testcase, 'assertion'):
                testcase.assertion.verify(context)
        except Exception as e:
            self.observer.testcase_fail(testcase, e)
            raise
        finally:
            self.observer.testcase_end(testcase)

    def run_step(self, step_name, context):
        """执行单个步骤（命令或故障）"""
        step = self.registry.get(step_name)
        step.execute(context)
''',

    "core/context.py": '''"""
Execution Context
用于存储测试执行过程中的上下文信息
包括节点信息、环境变量、测试参数等
"""
class Context(dict):
    """简单字典扩展，可直接存取任意上下文数据"""
    pass
''',

    "core/result.py": '''"""
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
''',

    # ---- Command ----
    "command/base.py": '''"""
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
''',

    "command/shell.py": '''"""
ShellCommand
通过执行 shell 命令实现原子操作
"""
import subprocess

from command.base import Command

class ShellCommand(Command):
    def __init__(self, cmd, expect=None):
        self.cmd = cmd
        self.expect = expect

    def execute(self, context):
        """执行 shell 命令并检查期望结果"""
        final_cmd = self.cmd.format(**context)
        print(f"[ShellCommand] execute: {final_cmd}")
        result = subprocess.run(final_cmd, shell=True, capture_output=True, text=True)
        output = result.stdout
        if self.expect and self.expect not in output:
            raise AssertionError(f"Expected '{self.expect}' in output")
        return output
''',

    # ---- Chaos ----
    "chaos/base.py": '''"""
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
''',

    "chaos/process.py": '''"""
Process Chaos
进程相关故障，例如 kill / restart
"""
import time
from chaos.base import Chaos
from command.shell import ShellCommand

class KillProcess(Chaos):
    def __init__(self, cmd, recover_cmd, duration):
        self.cmd = cmd
        self.recover_cmd = recover_cmd
        self.duration = duration

    def execute(self, context):
        """执行故障注入，并在 duration 后恢复"""
        ShellCommand(self.cmd).execute(context)
        time.sleep(self.duration)
        ShellCommand(self.recover_cmd).execute(context)
''',

    "chaos/network.py": '''"""
Network Chaos
网络隔离 / 延迟注入
"""
import time
from chaos.base import Chaos
from command.shell import ShellCommand

class NetworkPartition(Chaos):
    def __init__(self, cmd, recover_cmd, duration):
        self.cmd = cmd
        self.recover_cmd = recover_cmd
        self.duration = duration

    def execute(self, context):
        ShellCommand(self.cmd).execute(context)
        time.sleep(self.duration)
        ShellCommand(self.recover_cmd).execute(context)
''',

    # ---- DSL loader ----
    "dsl/loader.py": '''"""
DSL Loader
用于将 YAML 配置加载为 Command / Chaos / Testcase 对象
"""
import yaml

def load_yaml(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
''',

    # ---- Assert ----
    "assertor/base.py": '''"""
断言基类
每个断言必须实现 verify(context)
"""
class BaseAssert:
    def verify(self, context):
        raise NotImplementedError("Must implement verify")
''',

    "assertor/contains.py": '''"""
Contains 断言
检查输出是否包含期望文本
"""
from assertor.base import BaseAssert

class ContainsAssert(BaseAssert):
    def __init__(self, expected):
        self.expected = expected

    def verify(self, context):
        output = context.get("last_output", "")
        if self.expected not in output:
            raise AssertionError(f"Expected '{self.expected}' in output")
''',

    "assertor/eventually.py": '''"""
Eventually 断言
等待一定时间，直到条件满足或超时
"""
import time
from assertor.base import BaseAssert

class EventuallyAssert(BaseAssert):
    def __init__(self, check_func, timeout=60, interval=3):
        self.check_func = check_func
        self.timeout = timeout
        self.interval = interval

    def verify(self, context):
        end_time = time.time() + self.timeout
        last_exception = None
        while time.time() < end_time:
            try:
                self.check_func(context)
                return
            except Exception as e:
                last_exception = e
                time.sleep(self.interval)
        raise last_exception
''',

    # ---- Observability ----
    "observability/otel.py": '''"""
OpenTelemetry 初始化
用于 Trace / Metric 上报
"""
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

def init_otel(service_name="auto_test_framework"):
    """
    初始化 OpenTelemetry
    """
    tracer_provider = TracerProvider()
    trace.set_tracer_provider(tracer_provider)

    meter_provider = MeterProvider()
    metrics.set_meter_provider(meter_provider)
''',

    "observability/allure.py": '''"""
Allure 集成封装
用于测试报告生成
"""
def start_step(name):
    print(f"[Allure] start step: {name}")

def end_step(name):
    print(f"[Allure] end step: {name}")
''',

    # ---- cases / conf ----
    "cases/__init__.py": "",
    "conf/commands.yaml": "# 原子命令配置文件\n",
    "conf/chaos.yaml": "# 原子故障配置文件\n",
    "conf/testcases.yaml": "# 测试用例组合配置文件\n",
    "pytest.ini": "[pytest]\naddopts = -v --tb=short\n",
    "pyproject.toml": "[project]\nname = 'auto_test_framework'\n",
}


def mkdirs(root, dirs):
    for d in dirs:
        path = os.path.join(root, d)
        os.makedirs(path, exist_ok=True)
        print(f"Created dir: {path}")


def create_files(root, files):
    for path, content in files.items():
        full_path = os.path.join(root, path)
        dir_path = os.path.dirname(full_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Created file: {full_path}")


if __name__ == "__main__":
    mkdirs(ROOT_DIR, DIRS)
    create_files(ROOT_DIR, FILES)
    print(f"\n✅ 自动化测试框架骨架（带注释）已生成在 {ROOT_DIR} 下")
    print("💡 可以直接使用 pdoc / Sphinx 等工具生成开发者文档")
