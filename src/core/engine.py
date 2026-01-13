"""
Execution Engine
负责调度 testcase / step / chaos
所有 hook / command 均通过 runner 执行
"""

import time
from typing import Dict
from core.runner import Runner  # 新的统一 Runner

class ExecutionEngine:
    def __init__(self, registry, observer):
        self.registry = registry
        self.observer = observer
        self.runner = Runner()  # 统一执行入口

    # =========================
    # Testcase level
    # =========================

    def run_testcase(self, testcase: Dict, context: Dict):
        tc_name = testcase["name"]
        self.observer.testcase_start(tc_name)

        try:
            self._run_hooks(testcase.get("hooks", {}).get("before", []), context, phase="before")

            for step in testcase["steps"]:
                self.run_step(step, context)

            self._run_hooks(testcase.get("hooks", {}).get("after", []), context, phase="after")

        except Exception as e:
            self._run_hooks(testcase.get("hooks", {}).get("on_fail", []), context, phase="on_fail")
            self.observer.testcase_fail(tc_name, e)
            raise

        finally:
            self.observer.testcase_end(tc_name)

    # =========================
    # Step level
    # =========================

    def run_step(self, step: Dict, context: Dict):
        step_name = step["name"]
        print("run step " + step_name)
        cmd_ref = step.get("cmd_ref", step_name)

        obj = self.registry.get(cmd_ref)
        if obj is None:
            raise ValueError(
                f"[Engine Error] step '{step_name}' 引用的命令/故障 '{cmd_ref}' 未注册"
            )

        retry = step.get("retry", 1)
        timeout = step.get("timeout", None)

        self.observer.step_start(step_name)

        start_time = time.time()
        success = False
        last_exc = None

        try:
            import allure
            with allure.step(step_name):
                for attempt in range(1, retry + 1):
                    try:
                        self._execute_obj(obj, context, timeout)
                        self._verify_expect(step.get("expect"), context)
                        success = True
                        break
                    except Exception as e:
                        last_exc = e
                        context["last_error"] = str(e)
                        if attempt < retry:
                            time.sleep(1)
                        else:
                            raise
        finally:
            duration = time.time() - start_time
            self.observer.step_end(step_name, success, duration)

        if not success and last_exc:
            raise last_exc

    # =========================
    # Hook execution
    # =========================

    def _run_hooks(self, hooks, context, phase):
        for hook in hooks:
            self._run_hook(hook, context, phase)

    def _run_hook(self, hook_cmd, context, phase):
        self.observer.hook_start(phase, hook_cmd)
        try:
            self.runner.run(hook_cmd, context)
        finally:
            self.observer.hook_end(phase, hook_cmd)

    # =========================
    # Command / Chaos execution
    # =========================

    def _execute_obj(self, obj, context, timeout):
        """
        obj 必须提供 build_command(context) -> str | list
        由 Runner 执行
        """
        cmd = obj.build_command(context)
        return self.runner.run(cmd, context, timeout)

    # =========================
    # Expect / Assert
    # =========================

    def _verify_expect(self, expect, context):
        if not expect:
            return

        from assertor.contains import ContainsAssert
        from assertor.eventually import EventuallyAssert

        if "contains" in expect:
            ContainsAssert(expect["contains"]).verify(context)

        if "eventually" in expect:
            EventuallyAssert(
                lambda ctx: ContainsAssert(
                    expect["eventually"]["contains"]
                ).verify(ctx)
            ).verify(context)
