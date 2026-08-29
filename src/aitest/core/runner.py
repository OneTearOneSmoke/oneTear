"""Runner —— 单用例 / 套件的执行器。"""
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, List, Optional

from .context import Context
from .errors import AssertFailure, CommandFailure
from .render import resolve_args
from .result import Result


class Runner:
    def __init__(self, registry, *, max_workers: int = 1, replay_dir: str = "replays") -> None:
        self.registry = registry
        self.max_workers = max_workers
        self.replay_dir = replay_dir

    # ---------- 单条 ----------
    def run_case(self, case, *, ctx: Optional[Context] = None) -> Result:
        ctx = ctx or Context(case=case, params=case.params)
        ctx.meta["__registry__"] = self.registry
        started = time.time()
        self._notify("case_start", case, ctx)
        ok, err = True, None
        try:
            for step in case.fixture_setup:
                self._run_cmd(step, ctx)
            if case.run:
                self._run_cmd(case.run, ctx)
            for a in case.asserts:
                self._run_assert(a, ctx)
            for step in case.fixture_teardown:
                self._run_cmd(step, ctx)
        except (AssertFailure, CommandFailure) as e:
            ok, err = False, e
        except Exception as e:  # noqa: BLE001
            ok, err = False, e
        finished = time.time()
        result = Result(
            case_id=case.id,
            case_name=case.name,
            ok=ok,
            status="passed" if ok else "failed",
            ctx=ctx,
            error=err,
            started_at=started,
            finished_at=finished,
            duration_ms=(finished - started) * 1000,
        )
        self._notify("case_end", result)
        if not ok and case.record.on_failure:
            self._record_replay(result)
        return result

    # ---------- 套件 ----------
    def run_suite(
        self,
        cases: Iterable,
        *,
        only: Optional[Iterable[str]] = None,
        concurrency: int = 1,
    ) -> List[Result]:
        only_set = set(only or [])
        items = [c for c in cases if not only_set or c.id in only_set]
        if concurrency <= 1 or len(items) <= 1:
            return [self.run_case(c) for c in items]
        out: List[Result] = []
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futs = {ex.submit(self.run_case, c): c for c in items}
            for f in as_completed(futs):
                out.append(f.result())
        order = {id(c): i for i, c in enumerate(items)}
        out.sort(key=lambda r: order.get(id(r), 0))
        return out

    # ---------- 内部 ----------
    def _run_cmd(self, step, ctx: Context):
        try:
            cmd = self.registry.get_command(step.cmd)
        except KeyError as e:
            raise CommandFailure(step.cmd, str(e))
        try:
            args = resolve_args(step.args, ctx)
            out = cmd.run(args, ctx)
            ctx.run[step.cmd] = out
            return out
        except CommandFailure:
            raise
        except Exception as e:  # noqa: BLE001
            raise CommandFailure(step.cmd, f"{type(e).__name__}: {e}", cause=e)

    def _run_assert(self, a, ctx: Context):
        try:
            ass = self.registry.get_assertor(a.name)
        except KeyError as e:
            raise AssertFailure(a.name, str(e))
        try:
            args = resolve_args(a.args, ctx)
            ass.check(args, ctx)
        except AssertFailure:
            raise
        except Exception as e:  # noqa: BLE001
            raise AssertFailure(a.name, f"{type(e).__name__}: {e}", cause=e)

    def _notify(self, event: str, *args) -> None:
        for obs in self.registry.observers():
            fn = getattr(obs, event, None)
            if callable(fn):
                try:
                    fn(*args)
                except Exception as e:  # noqa: BLE001
                    print(f"[observer-error] {type(obs).__name__}.{event}: {e}")

    def _record_replay(self, result: Result) -> None:
        rec_dir = self.replay_dir
        try:
            if result.ctx and result.ctx.case and getattr(result.ctx.case.record, "dir", None):
                rec_dir = result.ctx.case.record.dir
        except Exception:
            pass
        d = Path(rec_dir)
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{result.case_id.replace('/', '_')}.{int(time.time() * 1000)}.json"
        path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
