# main.py
from core.registry import Registry
from core.engine import ExecutionEngine
from observability.allure import ObserverAllureProm
from core.context import Context
from dsl.loader import load_testcases
import itertools

def expand_matrix(matrix):
    keys = matrix.keys()
    for combo in itertools.product(*matrix.values()):
        yield dict(zip(keys, combo))

def run_all_testcases():
    registry = Registry()
    observer = ObserverAllureProm()
    engine = ExecutionEngine(registry, observer)
    testcases = load_testcases("conf/testcases")

    for tc in testcases:
        # 校验 testcase 是否合法
        registry.validate_testcase(tc)

        matrix = tc.get("matrix", {})
        combos = [m for m in expand_matrix(matrix)] if matrix else [{}]
        for combo in combos:
            context = Context()
            context.update(combo)
            context.update({"last_output": "Primary=node1"})  # demo 固定输出
            print(f"\n[Run] testcase: {tc.get('name')} | params: {combo}")
            try:
                engine.run_testcase(tc, context)
            except Exception as e:
                print(f"[Error] testcase {tc.get('name')} failed: {e}")

if __name__ == "__main__":
    run_all_testcases()
