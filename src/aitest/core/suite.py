"""Suite —— 用例集合、矩阵展开、查询、序列化。"""
import itertools
import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml

from .case import Case


def _matrix_keys(params: dict) -> List[str]:
    return [k for k, v in params.items() if isinstance(v, list)]


@dataclass
class Suite:
    cases: List[Case] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    # ---- load / add ----
    @classmethod
    def load_dir(cls, path: str, *, pattern: str = "*.y*ml") -> "Suite":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"suite path not found: {path}")
        s = cls()
        for f in sorted(p.rglob(pattern)):
            s.add_file(str(f))
        return s

    def add_file(self, path: str) -> "Suite":
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        if p.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(text) or {}
        elif p.suffix == ".json":
            data = json.loads(text) if text.strip() else {}
        else:
            raise ValueError(f"unsupported ext: {p.suffix}")
        if isinstance(data, dict) and "id" in data:
            self.cases.append(Case.from_dict(data, path=str(p)))
        elif isinstance(data, list):
            for item in data:
                self.cases.append(Case.from_dict(item, path=str(p)))
        else:
            raise ValueError(f"unsupported suite format: {p}")
        return self

    def add(self, case: Case) -> "Suite":
        self.cases.append(case)
        return self

    # ---- expand ----
    def expand(self) -> List[Case]:
        out: List[Case] = []
        for c in self.cases:
            keys = _matrix_keys(c.params)
            if not keys:
                out.append(c)
                continue
            values = [c.params[k] for k in keys]
            for combo in itertools.product(*values):
                fixed = {k: v for k, v in c.params.items() if k not in keys}
                fixed.update(dict(zip(keys, combo)))
                out.append(replace(c, params=fixed, raw=dict(c.raw)))
        return out

    # ---- query ----
    def filter(
        self,
        *,
        tags: Optional[Iterable[str]] = None,
        not_tags: Optional[Iterable[str]] = None,
        only: Optional[Iterable[str]] = None,
    ) -> "Suite":
        tags = set(tags or [])
        not_tags = set(not_tags or [])
        only_set = set(only or [])
        new = []
        for c in self.cases:
            if tags and not (set(c.tags) & tags):
                continue
            if not_tags and (set(c.tags) & not_tags):
                continue
            if only_set and c.id not in only_set:
                continue
            new.append(c)
        return Suite(cases=new, meta=self.meta)

    def search(self, keyword: str) -> "Suite":
        kw = keyword.lower()
        new = [c for c in self.cases if kw in c.id.lower() or kw in (c.name or "").lower()]
        return Suite(cases=new, meta=self.meta)

    def tag_index(self) -> Dict[str, List[str]]:
        idx: Dict[str, List[str]] = {}
        for c in self.cases:
            for t in c.tags:
                idx.setdefault(t, []).append(c.id)
        return idx

    def to_json(self) -> str:
        return json.dumps([c.to_dict() for c in self.cases], ensure_ascii=False, indent=2)

    def __len__(self) -> int:
        return len(self.cases)
