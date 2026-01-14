import yaml
from pathlib import Path
from domain.step import Step
from domain.testcase import TestCase
from domain.hooks import Hooks
from assertor.registry import build_asserter

def load_testcases(path: str, cmd_registry):
    cases = []

    for file in Path(path).glob("*.yaml"):
        with open(file) as f:
            conf = yaml.safe_load(f)

        steps = []
        for s in conf["steps"]:
            cmd_def = cmd_registry.get(s["cmd_ref"])
            asserter = build_asserter(s["expect"]) if "expect" in s else None
            steps.append(Step(s["name"], cmd_def, asserter))

        hooks = Hooks(**conf.get("hooks", {}))

        cases.append(
            TestCase(
                name=conf["name"],
                matrix=conf.get("matrix", {}),
                context=conf.get("context", {}),
                steps=steps,
                hooks=hooks,
            )
        )

    return cases
