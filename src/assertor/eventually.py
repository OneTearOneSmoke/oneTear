"""
Eventually 断言
等待一定时间，直到条件满足或超时
"""
import time
from assertor.base import BaseAssert

class EventuallyAssert(BaseAssert):
    def __init__(self, func, retries=5, interval=1):
        self.func = func
        self.retries = retries
        self.interval = interval

    def verify(self, context):
        for i in range(self.retries):
            try:
                self.func(context)
                print("[Assert] eventually OK")
                return
            except AssertionError:
                time.sleep(self.interval)
        raise AssertionError("Eventually assertion failed after retries")

