import json


class JsonReportObserver:
    name = "json_report"

    def __init__(self, path: str = "aitest-report.json") -> None:
        self.path = path
        self.results = []

    def case_start(self, case, ctx):
        pass

    def case_end(self, result):
        self.results.append(result)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self.results], f, ensure_ascii=False, indent=2)
