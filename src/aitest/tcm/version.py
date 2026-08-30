"""Case Versioning —— 内容指纹 + 语义版本。

提供：
  - `content_hash(case)`     : SHA-256 over normalized dict（去 path / raw / 时间戳）
  - `bump_semver(ver, kind)` : 语义版本自动 bump (major/minor/patch)
  - `parse_semver(s)`        : "1.2.3" → (1, 2, 3)
  - `format_semver(t)`       : (1, 2, 3) → "1.2.3"
  - `CaseVersion`            : 把 content_hash + semver 绑在一起

模块边界：不参与 EXF / TRM / TMRM；只是给用例一个稳定的"指纹 + 版本"。
"""
from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Tuple


_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_semver(s: str) -> Tuple[int, int, int]:
    m = _SEMVER_RE.match(s.strip())
    if not m:
        raise ValueError(f"invalid semver: {s!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def format_semver(t: Tuple[int, int, int]) -> str:
    a, b, c = t
    return f"{a}.{b}.{c}"


def bump_semver(ver: str, kind: str = "patch") -> str:
    """kind: major / minor / patch。"""
    a, b, c = parse_semver(ver)
    if kind == "major":
        return format_semver((a + 1, 0, 0))
    if kind == "minor":
        return format_semver((a, b + 1, 0))
    if kind == "patch":
        return format_semver((a, b, c + 1))
    raise ValueError(f"unknown bump kind: {kind}")


def _normalize_for_hash(d: Any) -> Any:
    """递归把 dict / list 排好序、转 JSON；剔除 'path'、'raw'、'created_at'。"""
    EXCLUDE = {"path", "raw", "created_at", "updated_at", "version"}
    if isinstance(d, dict):
        return {k: _normalize_for_hash(v) for k, v in sorted(d.items()) if k not in EXCLUDE}
    if isinstance(d, list):
        return [_normalize_for_hash(x) for x in d]
    if isinstance(d, tuple):
        return tuple(_normalize_for_hash(x) for x in d)
    return d


def content_hash(case_dict: dict, *, algo: str = "sha256") -> str:
    """稳定 hash：剔除时间戳 / path / raw 后求 SHA-256 前 12 位。"""
    norm = _normalize_for_hash(case_dict)
    blob = json.dumps(norm, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    h = hashlib.new(algo)
    h.update(blob)
    return h.hexdigest()[:12]


@dataclass
class CaseVersion:
    semver: str = "1.0.0"
    content_hash: str = ""

    def __str__(self) -> str:
        return f"{self.semver}+{self.content_hash}" if self.content_hash else self.semver

    @classmethod
    def from_dict(cls, d: dict) -> "CaseVersion":
        return cls(
            semver=d.get("semver", "1.0.0"),
            content_hash=content_hash(d),
        )
