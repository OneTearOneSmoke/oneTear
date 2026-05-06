import yaml
from pathlib import Path
from domain.step import Step
from domain.testcase import TestCase
from domain.hooks import Hooks
from assertor.registry import build_asserter


def _resolve_step_command_key(step_conf: dict) -> str:
    """
    Backward compatibility:
    - prefer cmd_ref
    - fallback to cmd (legacy alias of command name)
    """
    key = step_conf.get("cmd_ref") or step_conf.get("cmd")
    if not key:
        raise KeyError(f"step missing cmd_ref/cmd: {step_conf}")
    return key

def load_testcases(path: str, cmd_registry):
    cases = []

    for file in Path(path).glob("*.yaml"):
        with open(file) as f:
            conf = yaml.safe_load(f)

        steps = []
        for s in conf["steps"]:
            cmd_def = cmd_registry.get(_resolve_step_command_key(s))
            asserter = build_asserter(s["expect"]) if "expect" in s else None
            steps.append(Step(s["name"], cmd_def, asserter, retry=s.get("retry", {})))

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
