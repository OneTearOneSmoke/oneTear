"""
Execution Engine
负责调度测试用例、步骤（Step）和故障（Chaos），并触发断言。
支持 DAG / 序列执行。
"""
import time
class ExecutionEngine:
    def __init__(self, registry, observer):
        self.registry = registry
        self.observer = observer

    def run_testcase(self, testcase, context):
        """执行 YAML 配置驱动的 testcase"""
        self.observer.testcase_start(testcase["name"])
        try:
            # 执行 hooks before
            for cmd in testcase.get("hooks", {}).get("before", []):
                print(f"[Hook Before] {cmd}")

            for step in testcase["steps"]:
                self.run_step(step, context)

            # hooks after
            for cmd in testcase.get("hooks", {}).get("after", []):
                print(f"[Hook After] {cmd}")

        except Exception as e:
            for cmd in testcase.get("hooks", {}).get("on_fail", []):
                print(f"[Hook on_fail] {cmd}")
            self.observer.testcase_fail(testcase["name"], e)
            raise
        finally:
            self.observer.testcase_end(testcase["name"])

    def run_step(self, step, context):
        step_name = step["name"]
        cmd_ref = step.get("cmd_ref", step_name)
        obj = self.registry.get(cmd_ref)
        
        if obj is None:
            raise ValueError(f"[Engine Error] step '{step_name}' 对应的命令/故障 '{cmd_ref}' 没有在 registry 中注册")
        
        self.observer.step_start(step_name)
        start_time = time.time()
        success = True

        try:
            import allure
            with allure.step(f"{step_name}"):
                obj.execute(context)
                if "expect" in step:
                    self._verify_expect(step["expect"], context)
        except Exception as e:
            success = False
            raise e
        finally:
            duration = time.time() - start_time
            self.observer.step_end(step_name, success, duration)


    def _verify_expect(self, expect, context):
        from assertor.contains import ContainsAssert
        from assertor.eventually import EventuallyAssert

        if "contains" in expect:
            ContainsAssert(expect["contains"]).verify(context)
        if "eventually" in expect:
            EventuallyAssert(lambda ctx: ContainsAssert(expect["eventually"]["contains"]).verify(ctx)).verify(context)

