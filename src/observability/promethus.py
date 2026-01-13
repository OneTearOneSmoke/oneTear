# observability/prometheus.py
from prometheus_client import Counter, Histogram

TESTCASE_TOTAL = Counter(
    "onetear_testcase_total",
    "Total testcases",
    ["status"],
)

STEP_DURATION = Histogram(
    "onetear_step_duration_seconds",
    "Step duration",
    ["step"],
)


class PrometheusObserver:
    def testcase_end(self, name):
        TESTCASE_TOTAL.labels(status="success").inc()

    def testcase_fail(self, name, err):
        TESTCASE_TOTAL.labels(status="fail").inc()

    def step_end(self, name, success, duration):
        STEP_DURATION.labels(step=name).observe(duration)
