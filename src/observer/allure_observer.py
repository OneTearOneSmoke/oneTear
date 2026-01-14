import allure
from observer.base import BaseObserver

class AllureObserver(BaseObserver):
    def testcase_start(self, testcase, context):
        allure.dynamic.feature(testcase.name)

    def step_start(self, testcase, node, context):
        self.current_step = allure.step(f"{node.name} | context={context}")
        self.current_step.__enter__()

    def step_end(self, testcase, node, context, result):
        self.current_step.__exit__(None, None, None)

    def testcase_error(self, testcase, context, error):
        allure.attach(str(error), name="error", attachment_type=allure.attachment_type.TEXT)

    def testcase_end(self, testcase, context, success):
        pass
