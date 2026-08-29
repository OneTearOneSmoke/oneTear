from xml.sax.saxutils import escape


class JunitObserver:
    name = "junit"

    def __init__(self, path: str = "test-results.xml") -> None:
        self.path = path
        self.results = []

    def case_start(self, case, ctx):
        pass

    def case_end(self, result):
        self.results.append(result)
        tests = len(self.results)
        failures = sum(1 for r in self.results if not r.ok)
        cases = []
        for r in self.results:
            extra = ""
            if not r.ok:
                extra = f'<failure message="{escape(str(r.error))}"></failure>'
            cases.append(
                f'<testcase classname="{escape(r.case_id)}" '
                f'name="{escape(r.case_name)}" time="{r.duration_ms / 1000:.3f}">{extra}</testcase>'
            )
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<testsuite name="aitest" tests="{tests}" failures="{failures}">'
            + "".join(cases)
            + "</testsuite>"
        )
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(xml)
