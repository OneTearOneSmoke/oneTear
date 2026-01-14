from command.registry import CommandRegistry
from core.loader import load_testcases
from core.engine import ExecutionEngine
from observer.logger import LoggerObserver

# 加载命令
cmds = CommandRegistry()
cmds.load_dir("conf/command")  # 目录下所有 yaml 都会加载

# 初始化 Engine + Observer
engine = ExecutionEngine(cmds, observers=[LoggerObserver()])

# 加载所有 TestCase 并执行
for tc in load_testcases("conf/testcases", cmds):
    engine.run(tc)
