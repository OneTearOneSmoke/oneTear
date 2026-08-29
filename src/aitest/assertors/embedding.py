"""embedding_sim —— 简易 bag-of-words 余弦相似度（无第三方依赖）。"""
import math
from collections import Counter

from ..core.errors import AssertFailure


def _bow(text: str) -> dict:
    s = (text or "").lower()
    # 同时使用空格分词 + 字符 bigram，对中英文都友好
    tokens = []
    for w in s.split():
        tokens.append(w)
        if len(w) > 1:
            tokens.extend(w[i:i+2] for i in range(len(w)-1))
    return Counter(t for t in tokens if t)


def _cosine(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b.get(k, 0) for k in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class EmbeddingSim:
    name = "embedding_sim"

    def check(self, args, ctx):
        a = args.get("a", "")
        b = args.get("b", "")
        threshold = float(args.get("threshold", 0.5))
        sim = _cosine(_bow(a), _bow(b))
        if sim < threshold:
            raise AssertFailure(
                self.name, f"sim={sim:.3f} < threshold={threshold}"
            )
        return sim
