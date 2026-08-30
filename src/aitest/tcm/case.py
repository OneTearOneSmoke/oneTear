"""Case / CaseStep / CaseAssert / CaseRecord —— 纯数据用例模型。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CaseStep:
    cmd: str
    args: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[float] = None

    @classmethod
    def from_dict(cls, d: dict) -> "CaseStep":
        return cls(
            cmd=d["cmd"],
            args=dict(d.get("args") or {}),
            timeout=d.get("timeout"),
        )

    def to_dict(self) -> dict:
        out: Dict[str, Any] = {"cmd": self.cmd, "args": self.args}
        if self.timeout is not None:
            out["timeout"] = self.timeout
        return out


@dataclass
class CaseAssert:
    name: str
    args: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, key: str, val: Any) -> "CaseAssert":
        if isinstance(val, dict):
            return cls(name=key, args=dict(val))
        return cls(name=key, args={"value": val})

    def to_dict(self) -> dict:
        return {self.name: self.args}


@dataclass
class CaseRecord:
    on_failure: bool = False
    dir: str = "replays"

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "CaseRecord":
        if not d:
            return cls()
        return cls(
            on_failure=bool(d.get("on_failure", False)),
            dir=d.get("dir", "replays"),
        )

    def to_dict(self) -> dict:
        return {"on_failure": self.on_failure, "dir": self.dir}


@dataclass
class Case:
    id: str
    name: str = ""
    tags: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    fixture_setup: List[Any] = field(default_factory=list)
    fixture_teardown: List[Any] = field(default_factory=list)
    run: Any = None
    asserts: List[Any] = field(default_factory=list)
    record: Any = field(default_factory=CaseRecord)
    timeout: Optional[float] = None
    retries: int = 0
    severity: str = "normal"
    owner: str = ""
    source: str = "human"
    description: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)
    path: str = ""

    def __post_init__(self):
        if isinstance(self.record, dict):
            self.record = CaseRecord.from_dict(self.record)
        if isinstance(self.run, dict):
            self.run = CaseStep.from_dict(self.run)
        self.fixture_setup = [
            s if isinstance(s, CaseStep) else CaseStep.from_dict(s)
            for s in (self.fixture_setup or [])
        ]
        self.fixture_teardown = [
            s if isinstance(s, CaseStep) else CaseStep.from_dict(s)
            for s in (self.fixture_teardown or [])
        ]
        new_a = []
        for a in self.asserts or []:
            if isinstance(a, CaseAssert):
                new_a.append(a)
            elif isinstance(a, dict):
                if "name" in a and "args" in a:
                    new_a.append(CaseAssert(name=a["name"], args=dict(a.get("args") or {})))
                else:
                    name, args = next(iter(a.items()))
                    new_a.append(CaseAssert.from_dict(name, args))
            else:
                new_a.append(a)
        self.asserts = new_a

    @classmethod
    def from_dict(cls, d: dict, *, path: str = "") -> "Case":
        if "id" not in d:
            raise ValueError(f"case missing 'id' in {path or d}")
        fixture = d.get("fixture") or {}
        run = CaseStep.from_dict(d["run"]) if d.get("run") else None
        raw = d.get("asserts") or []
        asserts = []
        if isinstance(raw, dict):
            for k, v in raw.items():
                asserts.append(CaseAssert.from_dict(k, v))
        elif isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict) or len(item) != 1:
                    raise ValueError(f"assert item must be single-key dict: {item}")
                k, v = next(iter(item.items()))
                asserts.append(CaseAssert.from_dict(k, v))
        else:
            raise ValueError(f"asserts must be dict or list: {raw!r}")
        rec = CaseRecord.from_dict(d.get("record"))
        return cls(
            id=d["id"],
            name=d.get("name") or d["id"],
            tags=list(d.get("tags") or []),
            params=dict(d.get("params") or {}),
            fixture_setup=[CaseStep.from_dict(x) for x in (fixture.get("setup") or [])],
            fixture_teardown=[CaseStep.from_dict(x) for x in (fixture.get("teardown") or [])],
            run=run,
            asserts=asserts,
            record=rec,
            timeout=d.get("timeout"),
            retries=int(d.get("retries", 0) or 0),
            severity=d.get("severity", "normal"),
            owner=d.get("owner", ""),
            source=d.get("source", "human"),
            description=d.get("description", ""),
            raw=d,
            path=path,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "tags": list(self.tags),
            "params": self.params,
            "fixture": {
                "setup": [s.to_dict() for s in self.fixture_setup],
                "teardown": [s.to_dict() for s in self.fixture_teardown],
            },
            "run": self.run.to_dict() if self.run else None,
            "asserts": [a.to_dict() for a in self.asserts],
            "record": self.record.to_dict() if isinstance(self.record, CaseRecord) else self.record,
            "timeout": self.timeout,
            "retries": self.retries,
            "severity": self.severity,
            "owner": self.owner,
            "source": self.source,
            "description": self.description,
        }
