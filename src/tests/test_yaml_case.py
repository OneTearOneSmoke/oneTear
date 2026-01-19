import pytest
from core.command_registry import CommandRegistry
from core.testcase_registry import TestCaseRegistry
from core.engine import ExecutionEngine
from observer.logger import LoggerObserver
from observer.allure import AllureObserver

def pytest_generate_tests(metafunc):
    if "testcase" not in metafunc.fixturenames:
        return

    cmds = CommandRegistry()
    cmds.load_dir("conf/commands")

    cases = TestCaseRegistry()
    cases.load_dir("conf/testcases")

    params = []
    ids = []

    for tc in cases.all():
        params.append(tc)
        ids.append(tc.name)

    metafunc.parametrize("testcase", params, ids=ids)


@pytest.fixture
def engine():
    cmds = CommandRegistry()
    cmds.load_dir("conf/commands")

    observers = [
        LoggerObserver(),
        AllureObserver()
    ]
    return ExecutionEngine(observers, cmds)


def test_yaml_testcase(engine, testcase):
    context = testcase.context or {}
    engine.run_testcase(testcase, context)
