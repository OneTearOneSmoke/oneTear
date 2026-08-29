import json
import time
from pathlib import Path


class RecorderObserver:
    name = "recorder"

    def __init__(self, dir: str = "replays") -> None:
        self.dir = dir

    def case_start(self, case, ctx):
        pass

    def case_end(self, result):
        if result.ok:
            return
        d = Path(self.dir)
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{result.case_id.replace('/', '_')}.{int(time.time() * 1000)}.json"
        path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
