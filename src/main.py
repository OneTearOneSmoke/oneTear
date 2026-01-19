from core.command_registry import CommandRegistry
from core.testcase_registry import TestCaseRegistry
from core.engine import ExecutionEngine
from observer.logger import LoggerObserver
from observer.allure import AllureObserver

def main():
    """
    load all command which testcase used
    """
    cmds = CommandRegistry()
    cmds.load_dir("conf/commands")

    """
    load all testcase, a file difine a testcase
    """
    cases = TestCaseRegistry()
    cases.load_dir("conf/testcases")

    """
    testcase observer such as log,trace,allure only support log now
    """
    observers = [LoggerObserver(), AllureObserver()]


    """
    execute engine, execute command in the testcase
    1. run before hooks
    2. run steps list
    3. run after hooks
    """
    engine = ExecutionEngine(observers, cmds)

    for case in cases.all():
        for ctx in case.expand():
            engine.run_testcase(case, ctx) # run a testcase

if __name__ == "__main__":
    main()
