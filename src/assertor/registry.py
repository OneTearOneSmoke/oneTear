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
        return ContainsAsserter(text, eventually=True, timeout=timeout)

    raise ValueError(f"Unknown assertor: {conf}")
