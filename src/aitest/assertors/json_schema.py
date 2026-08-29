"""json_schema —— 用 jsonschema 校验（未安装时给出明确错误）。"""
from ..core.errors import AssertFailure


class JsonSchema:
    name = "json_schema"

    def check(self, args, ctx):
        try:
            import jsonschema  # type: ignore
        except ImportError as e:
            raise AssertFailure(
                self.name,
                f"jsonschema not installed: {e}. run: pip install jsonschema",
            )
        schema = args.get("schema")
        value = args.get("value")
        try:
            jsonschema.validate(instance=value, schema=schema)
        except Exception as e:  # noqa: BLE001
            raise AssertFailure(self.name, f"schema invalid: {e}")
