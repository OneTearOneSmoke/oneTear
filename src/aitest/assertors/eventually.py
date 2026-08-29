"""eventually —— 在 timeout 窗口内轮询某断言命中。"""
import time

from ..core.errors import AssertFailure


class Eventually:
    name = "eventually"

    def check(self, args, ctx):
        timeout = float(args.get("timeout", 5))
        interval = float(args.get("interval", 0.2))
        kind = args.get("kind", "contains")
        deadline = time.time() + timeout
        last_msg = ""
        while True:
            try:
                if kind == "contains":
                    v = args.get("value", "")
                    s = args.get("substr", "")
                    if s in (v or ""):
                        return True
                    last_msg = f"value={v!r} not contain {s!r}"
                elif kind == "eq":
                    v, e = args.get("value"), args.get("expect")
                    if v == e:
                        return True
                    last_msg = f"value={v!r} != expect={e!r}"
                elif kind == "truthy":
                    if bool(args.get("value")):
                        return True
                    last_msg = f"value={args.get('value')!r} not truthy"
                else:
                    raise AssertFailure(self.name, f"unknown kind: {kind}")
            except AssertFailure:
                raise
            if time.time() >= deadline:
                raise AssertFailure(self.name, f"eventually timeout: {last_msg}")
            time.sleep(interval)
