"""llm_judge —— 用 LLM 作为评审。"""
import json
import re

from ..core.errors import AssertFailure


def _extract_score(text: str):
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "score" in data:
            return float(data["score"])
    except Exception:  # noqa: BLE001
        pass
    m = re.search(r"score[^0-9]*?([0-9]+(?:\.[0-9]+)?)", text or "", re.I)
    if m:
        try:
            return float(m.group(1))
        except Exception:  # noqa: BLE001
            return None
    return None


class LLMJudge:
    name = "llm_judge"

    def check(self, args, ctx):
        reg = ctx.meta.get("__registry__")
        if reg is None:
            raise AssertFailure(self.name, "no registry in context")
        provider_name = args.get("provider", "echo")
        try:
            provider = reg.get_provider(provider_name)
        except KeyError as e:
            raise AssertFailure(self.name, str(e))
        prompt = args.get("prompt", "")
        threshold = float(args.get("threshold", 0.5))
        rubric = args.get(
            "rubric",
            "You are a strict reviewer. Reply ONLY a JSON: "
            '{"score": 0~1, "reason": "..."}',
        )
        try:
            out = provider.complete(f"{rubric}\n\n{prompt}")
        except Exception as e:  # noqa: BLE001
            raise AssertFailure(self.name, f"provider error: {e}")
        score = _extract_score(out)
        if score is None:
            raise AssertFailure(self.name, f"score not found in: {out!r}")
        if score < threshold:
            raise AssertFailure(
                self.name, f"score={score} < threshold={threshold}; raw={out[:200]}"
            )
        return {"score": score, "raw": out}
