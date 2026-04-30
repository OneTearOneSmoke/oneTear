from assertor.contains import ContainsAsserter

def build_asserter(conf: dict):
    """
    conf: dict, 可以是:
      {"contains": "..."}             -> 普通 assert
      {"eventually": {"contains": "...", "timeout": 5}} -> Eventually assert
    """
    if "contains" in conf:
        return ContainsAsserter(conf["contains"])
    elif "eventually" in conf:
        eventual_conf = conf["eventually"]
        text = eventual_conf["contains"]
        timeout = eventual_conf.get("timeout", 5)
        interval = eventual_conf.get("interval", 0.5)
        max_retries = eventual_conf.get("max_retries")
        return ContainsAsserter(
            text,
            eventually=True,
            timeout=timeout,
            interval=interval,
            max_retries=max_retries,
        )

    raise ValueError(f"Unknown assertor: {conf}")
