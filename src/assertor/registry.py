from assertor.contains import ContainsAsserter

def build_asserter(conf: dict):
    """
    conf: dict, 可以是:
      {"contains": "..."} -> 普通 contains assert
      {"return_code": 0} -> 返回码 assert
      {"contains": "...", "return_code": 0} -> contains + 返回码 assert
      {"eventually": {"contains": "...", "timeout": 5}} -> Eventually assert
    """
    if "eventually" in conf:
        eventual_conf = conf["eventually"]
        text = eventual_conf.get("contains")
        timeout = eventual_conf.get("timeout", 5)
        interval = eventual_conf.get("interval", 0.5)
        max_retries = eventual_conf.get("max_retries")
        expected_rc = eventual_conf.get("return_code", eventual_conf.get("rc"))
        return ContainsAsserter(
            text,
            eventually=True,
            timeout=timeout,
            interval=interval,
            max_retries=max_retries,
            expected_rc=expected_rc,
        )

    if "contains" in conf or "return_code" in conf or "rc" in conf:
        text = conf.get("contains")
        expected_rc = conf.get("return_code", conf.get("rc"))
        return ContainsAsserter(text, expected_rc=expected_rc)

    raise ValueError(f"Unknown assertor: {conf}")
