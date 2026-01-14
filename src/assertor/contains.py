from jinja2 import Environment, StrictUndefined
import time

_env = Environment(undefined=StrictUndefined)

class ContainsAsserter:
    def __init__(self, text: str, eventually=False, timeout=5):
        self.raw = text
        self.text = text
        self.eventually = eventually
        self.timeout = timeout

    def render(self, context: dict):
        tpl = _env.from_string(self.raw)
        return ContainsAsserter(tpl.render(**context), eventually=self.eventually, timeout=self.timeout)

    def assert_result(self, result: dict):
        if not self.eventually:
            if self.text not in result["stdout"]:
                raise AssertionError(f"expect stdout contains '{self.text}', got:\n{result['stdout']}")
        else:
            end_time = time.time() + self.timeout
            last_exc = None
            while time.time() < end_time:
                if self.text in result["stdout"]:
                    return
                last_exc = AssertionError(f"expect stdout contains '{self.text}', got:\n{result['stdout']}")
                time.sleep(0.5)
            raise last_exc
