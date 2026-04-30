from jinja2 import Environment, StrictUndefined
import time

_env = Environment(undefined=StrictUndefined)

class ContainsAsserter:
    def __init__(self, text: str, eventually=False, timeout=5, interval=0.5, max_retries=None):
        self.raw = text
        self.text = text
        self.eventually = eventually
        self.timeout = timeout
        self.interval = interval
        self.max_retries = max_retries

    def render(self, context: dict):
        tpl = _env.from_string(self.raw)
        return ContainsAsserter(
            tpl.render(**context),
            eventually=self.eventually,
            timeout=self.timeout,
            interval=self.interval,
            max_retries=self.max_retries,
        )

    def assert_result(self, result: dict, retry_fn=None, retry_policy=None):
        if not self.eventually:
            if self.text not in result["stdout"]:
                raise AssertionError(f"expect stdout contains '{self.text}', got:\n{result['stdout']}")
        else:
            retry_policy = retry_policy or {}
            timeout = retry_policy.get("timeout", self.timeout)
            interval = retry_policy.get("interval", self.interval)
            max_retries = retry_policy.get("max_retries", self.max_retries)

            end_time = time.time() + timeout
            last_exc = None
            retries_done = 0
            while True:
                if self.text in result["stdout"]:
                    return

                last_exc = AssertionError(f"expect stdout contains '{self.text}', got:\n{result['stdout']}")
                timed_out = time.time() >= end_time
                retry_exhausted = max_retries is not None and retries_done >= max_retries
                if timed_out or retry_exhausted:
                    raise last_exc

                if retry_fn is not None:
                    result = retry_fn()
                    retries_done += 1

                time.sleep(interval)
