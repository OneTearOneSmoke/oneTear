# main.py
"""
主入口
1. 加载 Registry（命令 & Chaos）
2. 加载 Observer（Allure + Prometheus/Trace）
3. 加载测试用例（YAML）
4. 扩展矩阵参数
5. 调用 ExecutionEngine 运行 testcase
"""

from core.registry import Registry
from core.engine import ExecutionEngine
from core.context import Context
from dsl.loader import load_testcases
import itertools
from observability.composite import CompositeObserver
from observability.allure import AllureObserver
from observability.promethus import PrometheusObserver
from observability.logging import LoggingObserver

def expand_matrix(matrix: dict):
    """矩阵参数展开，返回所有组合"""
    if not matrix:
        yield {}
        return
    keys = list(matrix.keys())
    for combo in itertools.product(*matrix.values()):
        yield dict(zip(keys, combo))


def run_all_testcases():
    # 1️⃣ 初始化全局组件
    registry = Registry()                # 从 YAML 加载 commands/chaos
    #observer = ObserverAllureProm()     # Allure + Trace
    observer = CompositeObserver(
        LoggingObserver(),
        AllureObserver(),
        PrometheusObserver(),
    )
    engine = ExecutionEngine(registry, observer)

    # 2️⃣ 加载所有测试用例
    testcases = load_testcases("conf/testcases")

    # 3️⃣ 遍历 testcase
    for tc in testcases:
        # 校验 testcase 是否合法
        registry.validate_testcase(tc)

        # 4️⃣ 展开矩阵参数
        matrix = tc.get("matrix", {})
        for combo in expand_matrix(matrix):
            # 上下文从 testcase 配置 + 矩阵参数
            context = Context()
            # 将 testcase 中 context 配置加载到 Context
            context_config = tc.get("context", {})
            context.update(context_config)
            # 矩阵参数覆盖 context
            context.update(combo)

            print(f"\n[Run] testcase: {tc.get('name')} | params: {combo}")

            try:
                engine.run_testcase(tc, context)
            except Exception as e:
                print(f"[Error] testcase {tc.get('name')} failed: {e}")


if __name__ == "__main__":
    run_all_testcases()
