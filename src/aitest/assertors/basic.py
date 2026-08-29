"""基础断言: eq / ne / contains / regex / truthy。"""
import re

from ..core.errors import AssertFailure


class Eq:
    name = "eq"

    def check(self, args, ctx):
        v, e = args.get("value"), args.get("expect")
        if v != e:
            raise AssertFailure(self.name, f"value={v!r} expect={e!r}")


class Ne:
    name = "ne"

    def check(self, args, ctx):
        v, e = args.get("value"), args.get("expect")
        if v == e:
            raise AssertFailure(self.name, f"value==expect both={v!r}")


class Contains:
    name = "contains"

    def check(self, args, ctx):
        v = args.get("value", "")
        s = args.get("substr", "")
        if s not in (v or ""):
            raise AssertFailure(self.name, f"value={v!r} not contain {s!r}")


class Regex:
    name = "regex"

    def check(self, args, ctx):
        v = args.get("value", "")
        p = args.get("pattern", "")
        if not re.search(p, v or ""):
            raise AssertFailure(self.name, f"value={v!r} not match /{p}/")


class Truthy:
    name = "truthy"

    def check(self, args, ctx):
        v = args.get("value")
        if not bool(v):
            raise AssertFailure(self.name, f"value={v!r} is falsy")
