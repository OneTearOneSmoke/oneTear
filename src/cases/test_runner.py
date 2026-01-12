import pytest
import itertools
import time
from dsl.loader import load_testcases, load_commands, load_chaos
from core.engine import ExecutionEngine
from observability.allure import ObserverAllureProm
from command.shell import ShellCommand
from chaos.process import KillProcess
from core.context import Context

def build_registry():
    registry = {}
    for cmd_conf in load_commands("conf/commands.yaml"):
        registry[cmd_conf["name"]] = ShellCommand(cmd_conf["cmd"])
    for chaos_conf in load_chaos("conf/chaos.yaml"):
        registry[chaos_conf["name"]] = KillProcess(
            chaos_conf["cmd"],
            chaos_conf.get("recover_cmd",""),
            chaos_conf.get("duration",0)
        )
    return registry

def expand_matrix(matrix):
    keys = matrix.keys()
    for combo in itertools.product(*matrix.values()):
        yield dict(zip(keys, combo))

registry = build_registry()
observer = ObserverAllureProm()
engine = ExecutionEngine(registry, observer)
testcases = load_testcases("conf/testcases")

param_list = []
for tc in testcases:
    matrix = tc.get("matrix", {})
    if matrix:
        for combo in expand_matrix(matrix):
            param_list.append((tc, combo))
    else:
        param_list.append((tc, {}))

# 安全生成 pytest ID
def make_test_id(param):
    # param 直接就是 tuple (testcase, matrix_params)
    tc, matrix_params = param
    tc_name = tc.get("name") if isinstance(tc, dict) else "unknown"
    matrix_str = "_".join(f"{k}{v}" for k,v in matrix_params.items())
    return f"{tc_name}_{matrix_str}" if matrix_str else tc_name

@pytest.mark.parametrize("testcase,matrix_params", param_list, ids=[make_test_id(p) for p in param_list])
def test_yaml_testcase(testcase, matrix_params):
    context = Context()
    context.update(matrix_params)
    context.update({"last_output":"Primary=node1"})
    engine.run_testcase(testcase, context)
