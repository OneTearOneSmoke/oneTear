class ExecutionEngine:
    def __init__(self, observers=None, command_registry=None):
        self.observers = observers or []
        self.command_registry = command_registry

    def run_testcase(self, testcase, context):
        ctx = dict(context)   # 每个 testcase 独立 context
        success = False
        nodes = []

        self._notify("testcase_start", testcase, ctx)

        try:
            nodes = testcase.get_nodes(self.command_registry)

            for node in nodes:
                self._run_step(testcase, node, ctx)

            success = True

        except Exception as e:
            # testcase 级别错误
            self._notify("testcase_error", testcase, ctx, e)

            # on_fail hooks（只在失败时执行）
            self._run_onfail_hooks(testcase, nodes, ctx)

            # 抛给 pytest / 上层
            raise

        finally:
            self._notify("testcase_end", testcase, ctx, success)

    # =========================
    # Step execution
    # =========================

    def _run_step(self, testcase, node, ctx):
        self._notify("step_start", testcase, node, ctx)

        try:
            result = node.run(ctx)

        except Exception as e:
            # node.run 内部异常，但可能带部分 result
            result = getattr(e, "result", None)

            self._notify(
                "step_error",
                testcase,
                node,
                ctx,
                e,
                result,
            )
            raise

        else:
            # 标准化 context 注入
            self._update_context(ctx, result)

            self._notify(
                "step_end",
                testcase,
                node,
                ctx,
                result,
            )

    # =========================
    # Hooks
    # =========================

    def _run_onfail_hooks(self, testcase, nodes, ctx):
        for node in nodes:
            if not node.name.startswith("hook_onfail"):
                continue

            try:
                self._notify("step_start", testcase, node, ctx)
                result = node.run(ctx)
                self._notify("step_end", testcase, node, ctx, result)

            except Exception as e:
                # hook 本身失败不应再影响 testcase 结果
                self._notify(
                    "step_error",
                    testcase,
                    node,
                    ctx,
                    e,
                    getattr(e, "result", None),
                )

    # =========================
    # Helpers
    # =========================

    def _update_context(self, ctx, result):
        if not result:
            return

        ctx["last_stdout"] = result.get("stdout")
        ctx["last_stderr"] = result.get("stderr")
        ctx["last_rc"] = result.get("rc")

    def _notify(self, event, *args):
        for obs in self.observers:
            fn = getattr(obs, event, None)
            if not callable(fn):
                continue

            try:
                fn(*args)
            except Exception as e:
                # observer 出错 ≠ 执行出错
                print(
                    f"[ObserverError] "
                    f"{obs.__class__.__name__}.{event}: {e}"
                )
