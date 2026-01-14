from core.command_registry import CommandRegistry
from core.testcase_registry import TestCaseRegistry
from core.engine import ExecutionEngine
from observer.logger import LoggerObserver

def main():
    cmds = CommandRegistry()
    cmds.load_dir("conf/commands")

    cases = TestCaseRegistry()
    cases.load_dir("conf/testcases")

    observers = [LoggerObserver()]

    engine = ExecutionEngine(observers, cmds)

    for case in cases.all():
        for ctx in case.expand():
            engine.run_testcase(case, ctx)

if __name__ == "__main__":
    main()
