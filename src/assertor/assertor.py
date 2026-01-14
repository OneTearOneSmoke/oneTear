import time
from jinja2 import Template

class Assertor:
    def check(self, result, expect, context):
        if not expect:
            return
        contains = expect.get("contains")
        eventually = expect.get("eventually")
        if contains:
            contains = Template(contains).render(**context)
        if eventually:
            timeout = float(eventually)
            start = time.time()
            while True:
                if contains in result["stdout"]:
                    return
                if time.time() - start > timeout:
                    raise AssertionError(f"Eventually timeout: expect [{contains}], got [{result['stdout']}]")
                time.sleep(0.5)
        else:
            if contains and contains not in result["stdout"]:
                raise AssertionError(f"expect contains [{contains}], got [{result['stdout']}]")
