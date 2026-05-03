from jinja2 import Environment, StrictUndefined
import time

_env = Environment(undefined=StrictUndefined)

class ContainsAsserter:
    def __init__(
        self,
        text: str | None,
        eventually=False,
        timeout=5,
        interval=0.5,
        max_retries=None,
        expected_rc=None,
    ):
        self.raw = text
        self.text = text
        self.eventually = eventually
        self.timeout = timeout
        self.interval = interval
        self.max_retries = max_retries
        self.expected_rc = expected_rc

    def render(self, context: dict):
        rendered_text = None
        if self.raw is not None:
            tpl = _env.from_string(self.raw)
            rendered_text = tpl.render(**context)
        return ContainsAsserter(
            rendered_text,
            eventually=self.eventually,
            timeout=self.timeout,
            interval=self.interval,
            max_retries=self.max_retries,
            expected_rc=self.expected_rc,
        )

    def assert_result(self, result: dict, retry_fn=None, retry_policy=None):
        if not self.eventually:
            self._assert_once(result)
        else:
            retry_policy = retry_policy or {}
            timeout = retry_policy.get("timeout", self.timeout)
            interval = retry_policy.get("interval", self.interval)
            max_retries = retry_policy.get("max_retries", self.max_retries)

            end_time = time.time() + timeout
            last_exc = None
            retries_done = 0
            while True:
                try:
                    self._assert_once(result)
                    return
                except AssertionError as exc:
                    last_exc = exc
                timed_out = time.time() >= end_time
                retry_exhausted = max_retries is not None and retries_done >= max_retries
                if timed_out or retry_exhausted:
                    raise last_exc

                if retry_fn is not None:
                    result = retry_fn()
                    retries_done += 1

                time.sleep(interval)

    def _assert_once(self, result: dict):
        stdout = result.get("stdout", "")
        rc = result.get("rc")

        if self.text is not None and self.text not in stdout:
            raise AssertionError(f"expect stdout contains '{self.text}', got:\n{stdout}")

        if self.expected_rc is None:
            return

        if isinstance(self.expected_rc, (list, tuple, set)):
            ok = rc in self.expected_rc
        else:
            ok = rc == self.expected_rc
        if not ok:
            raise AssertionError(f"expect return code {self.expected_rc}, got {rc}")
