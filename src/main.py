from command.registry import CommandRegistry
from core.loader import load_testcases
from core.engine import ExecutionEngine
from observer.logger import LoggerObserver


def _build_observers():
    observers = [LoggerObserver()]
    try:
        from observer.allure import AllureObserver
        observers.append(AllureObserver())
    except Exception:
        # Keep CLI execution available even when allure runtime is absent.
        pass
    return observers

# 加载命令
cmds = CommandRegistry()
cmds.load_dir("conf/command")  # 目录下所有 yaml 都会加载

# 初始化 Engine + Observer
engine = ExecutionEngine(cmds, observers=_build_observers())

# 加载所有 TestCase 并执行
for tc in load_testcases("conf/testcases", cmds):
    engine.run(tc)
