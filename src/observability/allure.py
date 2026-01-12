"""
Allure 集成封装
用于测试报告生成
"""
import time, allure
from prometheus_client import Counter, Summary, start_http_server

STEP_TIME = Summary('step_execution_seconds', 'Step execution time', ['step'])
STEP_STATUS = Counter('step_status_total', 'Step success/failure', ['step', 'status'])
start_http_server(18000)

class ObserverAllureProm:
    def testcase_start(self, name):
        print(f"[Trace] testcase_start: {name}")

    def testcase_end(self, name):
        print(f"[Trace] testcase_end: {name}")

    def testcase_fail(self, name, exception):
        print(f"[Trace] testcase_fail: {name}, {exception}")

    def step_start(self, step_name):
        print(f"[Trace] step_start: {step_name}")

    def step_end(self, step_name, success=True, duration=0):
        print(f"[Trace] step_end: {step_name}, success={success}, duration={duration:.2f}s")
        STEP_TIME.labels(step=step_name).observe(duration)
        STEP_STATUS.labels(step=step_name, status='success' if success else 'fail').inc()

