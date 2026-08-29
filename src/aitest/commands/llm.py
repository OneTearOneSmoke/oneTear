"""llm.query —— 调用已注册的 LLM provider。"""
from ..core.errors import CommandFailure


class LLMQuery:
    name = "llm.query"

    def run(self, args, ctx):
        reg = ctx.meta.get("__registry__")
        if reg is None:
            raise CommandFailure(self.name, "no registry in context")
        provider_name = args.get("provider", "echo")
        prompt = args.get("prompt", "")
        options = dict(args.get("options") or {})
        try:
            provider = reg.get_provider(provider_name)
        except KeyError as e:
            raise CommandFailure(self.name, str(e))
        try:
            text = provider.complete(prompt, **options)
        except Exception as e:  # noqa: BLE001
            raise CommandFailure(self.name, f"provider error: {e}")
        return {"text": text, "provider": provider_name}
