# observability/logging.py
import logging

log = logging.getLogger("onetear")


class LoggingObserver:
    def testcase_start(self, name):
        log.info(f"[TC START] {name}")

    def testcase_end(self, name):
        log.info(f"[TC END] {name}")

    def testcase_fail(self, name, err):
        log.error(f"[TC FAIL] {name}: {err}")

    def step_start(self, name):
        log.info(f"  [STEP] {name}")

    def step_end(self, name, success, duration):
        log.info(
            f"  [STEP END] {name} success={success} duration={duration:.2f}s"
        )

    def hook_start(self, phase, cmd):
        log.info(f"  [HOOK {phase}] {cmd}")

    def hook_end(self, phase, cmd):
        pass
