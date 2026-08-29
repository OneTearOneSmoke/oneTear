class LoggerObserver:
    name = "logger"

    def case_start(self, case, ctx):
        print(f"[case] start   {case.id}")

    def case_end(self, result):
        flag = "PASS" if result.ok else "FAIL"
        suffix = "" if result.ok else f" error={result.error}"
        print(f"[case] {flag:<6} {result.case_id} ({result.duration_ms:.2f} ms){suffix}")
