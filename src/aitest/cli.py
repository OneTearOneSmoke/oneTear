"""aitest CLI —— 5 个命令：run / ls / show / lint / diff / new / results。"""
import argparse
import json
import sys
import time
import uuid
from pathlib import Path

from .core.registry import Registry
from .core.state import Status, is_pass
from .core.runner import Runner
from .core.suite import Suite
from .observers.json_report import JsonReportObserver
from .observers.junit import JunitObserver
from .observers.logger import LoggerObserver
from .observers.recorder import RecorderObserver



def _build_default_registry() -> Registry:
    from .assertors.ast_struct import AstStruct
    from .assertors.basic import Contains, Eq, Ne, Regex, Truthy
    from .assertors.embedding import EmbeddingSim
    from .assertors.eventually import Eventually
    from .assertors.json_schema import JsonSchema
    from .assertors.llm_judge import LLMJudge
    from .assertors.property import Property
    from .commands.ast_diff import AstDiff
    from .commands.builtin import CleanTmp, MakeTmp, SeedRng, Sleep
    from .commands.http import HttpRequest
    from .commands.llm import LLMQuery
    from .commands.python import PythonEval
    from .commands.shell import ShellRun
    from .providers.echo import EchoProvider
    from .providers.openai import OpenAIProvider

    reg = Registry()
    for c in (ShellRun, PythonEval, HttpRequest, LLMQuery, AstDiff, SeedRng, MakeTmp, CleanTmp, Sleep):
        reg.command(instance=c())
    for a in (Eq, Ne, Contains, Regex, Truthy, JsonSchema, EmbeddingSim, LLMJudge, AstStruct, Property, Eventually):
        reg.assertor(instance=a())
    reg.provider(instance=EchoProvider())
    reg.provider(instance=OpenAIProvider())
    reg.observer(LoggerObserver())
    return reg


def _load_suite(args) -> Suite:
    suite = Suite.load_dir(args.suite, pattern=args.pattern)
    if getattr(args, "tag", None):
        suite = suite.filter(tags=args.tag)
    if getattr(args, "not_tag", None):
        suite = suite.filter(not_tags=args.not_tag)
    if getattr(args, "only", None):
        suite = suite.filter(only=args.only)
    return suite


def cmd_run(args) -> int:
    reg = _build_default_registry()
    if getattr(args, "junit", None):
        reg.observer(JunitObserver(args.junit))
    if getattr(args, "json_report", None):
        reg.observer(JsonReportObserver(args.json_report))
    if getattr(args, "recorder", None):
        reg.observer(RecorderObserver(args.recorder))

    suite = _load_suite(args)
    cases = suite.expand()

    # v0.5: --store 接 Result-Store；--concurrency>1 走进程级 WorkerPool
    store = None
    if getattr(args, "store", None):
        from .core.store import ResultStore
        store = ResultStore(args.store)

    concurrency = max(1, int(getattr(args, "concurrency", 1) or 1))
    if concurrency > 1 or store is not None:
        from .core.worker import WorkerPool, Task, RetryPolicy
        from .core.case import Case as _Case
        tasks = []
        for c in cases:
            # matrix 展开后每个 case 走一遍；这里把 case_id 拼上序号保证唯一
            t = Task(
                task_id=str(uuid.uuid4()),
                case=c,
                retry=RetryPolicy(max_attempts=1),
            )
            tasks.append(t)
        pool = WorkerPool(max_workers=concurrency, store=store)
        results_raw = pool.run(tasks)
        # 转成 Runner-style Result（保留 observers 调用）
        from .core.result import Result as _R
        from .core.context import Context
        results = []
        for r in results_raw:
            ctx = Context(case=_Case(id=r["case_id"], name=r.get("case_name") or r["case_id"]))
            ctx.params = r.get("params") or {}
            ctx.run = r.get("run_output") or {}
            results.append(_R(
                case_id=r["case_id"], case_name=r.get("case_name") or r["case_id"],
                ok=r.get("ok", False), status=r.get("status", "ERROR"),
                ctx=ctx, error=Exception(r["error_message"]) if r.get("error_message") else None,
            ))
        if store is not None:
            store.close()
    else:
        runner = Runner(reg)
        results = runner.run_suite(cases, only=args.only, concurrency=1)

    bad = [r for r in results if not r.ok]
    print(f"\n=== {len(results)} cases, {len(bad)} failed ===")
    for r in bad:
        print(f"  - {r.case_id}: {r.error}")
    return 0 if not bad else 1


def cmd_ls(args) -> int:
    suite = _load_suite(args)
    for c in suite.cases:
        tags = " ".join(f"#{t}" for t in c.tags)
        print(f"{c.id}\t{c.name}\t{tags}")
    return 0


def cmd_show(args) -> int:
    import yaml
    suite = _load_suite(args)
    for c in suite.cases:
        if c.id == args.id or c.name == args.id:
            print(yaml.safe_dump(c.to_dict(), allow_unicode=True, sort_keys=False))
            return 0
    print(f"not found: {args.id}")
    return 1


def cmd_lint(args) -> int:
    try:
        suite = _load_suite(args)
    except Exception as e:  # noqa: BLE001
        print(f"lint error: {e}")
        return 1
    print(f"OK: {len(suite.cases)} cases")
    return 0


def cmd_diff(args) -> int:
    a = Suite.load_dir(args.a, pattern=args.pattern)
    b = Suite.load_dir(args.b, pattern=args.pattern)
    ids_a = {c.id for c in a.cases}
    ids_b = {c.id for c in b.cases}
    print(f"only in A: {sorted(ids_a - ids_b)}")
    print(f"only in B: {sorted(ids_b - ids_a)}")
    print(f"common   : {len(ids_a & ids_b)}")
    return 0


def cmd_dryrun(args) -> int:
    """Dryrun：使用 mock 插件跑一遍，不触发真实副作用。"""
    from .plugin_proto.mock import install_mock
    from .core.runner import Runner
    suite = _load_suite(args)
    cases = suite.expand()

    reg = _build_default_registry()
    install_mock(reg)
    if getattr(args, "junit", None):
        reg.observer(JunitObserver(args.junit))

    runner = Runner(reg)
    results = runner.run_suite(cases, only=args.only, concurrency=args.concurrency)
    bad = [r for r in results if not r.ok]
    print(f"\n[dryrun] {len(results)} cases, {len(bad)} failed (mock mode)")
    for r in bad:
        print(f"  - {r.case_id}: {r.error}")
    return 0 if not bad else 1


def cmd_plugin_server(args) -> int:
    """启动 JSON-over-stdio 插件服务器（v0.5 临时，v0.8 切 gRPC）。"""
    from .plugin_proto.server import PluginServer
    PluginServer(dryrun=args.dryrun).serve_forever()
    return 0


def cmd_results(args) -> int:
    from .core.store import ResultStore
    store = ResultStore(args.store)
    try:
        if args.summary:
            s = store.summary()
            for k, v in s.items():
                print(f"{k:<10} {v}")
            return 0
        if args.case:
            rows = store.list_by_case(args.case, limit=args.limit)
        elif args.plan:
            rows = store.list_by_plan(args.plan, limit=args.limit)
        elif args.status:
            rows = store.list_by_status(args.status, limit=args.limit)
        else:
            rows = store.recent(limit=args.limit)
        for r in rows:
            dur = f"{r.duration_ms:.1f}ms" if r.duration_ms is not None else "-"
            ok = is_pass(Status(r.status))
            err = f" err={r.error_code}" if (not ok) or r.error_code else ""
            print(f"{r.task_id:<40} {r.case_id:<28} {r.status:<8} {dur:>10}{err}")
        print(f"--- {len(rows)} row(s) ---")
    finally:
        store.close()
    return 0


def cmd_new(args) -> int:
    import yaml
    from .core.case import Case

    case = Case(
        id=args.id or "auto.replay.case",
        name=args.name or "auto from replay",
        tags=["auto-mined"],
        source="auto-mined",
        description="Generated by `aitest new`",
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        yaml.safe_dump(case.to_dict(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"wrote {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aitest", description="AI 时代极简测试框架")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp, *, with_only: bool = True):
        sp.add_argument("--suite", default="cases")
        sp.add_argument("--pattern", default="*.y*ml")
        sp.add_argument("--tag", action="append", default=[])
        sp.add_argument("--not-tag", action="append", dest="not_tag", default=[])
        if with_only:
            sp.add_argument("--only", action="append", default=[])

    pr = sub.add_parser("run", help="run a suite")
    add_common(pr)
    pr.add_argument("--concurrency", type=int, default=1)
    pr.add_argument("--junit", help="junit xml path")
    pr.add_argument("--json-report", dest="json_report", help="json report path")
    pr.add_argument("--recorder", help="replay dir")
    pr.add_argument("--store", help="Result-Store SQLite path (persist every result)")
    pr.add_argument("--dryrun", action="store_true", help="dryrun: use mock plugin target (no real side-effect)")
    pr.set_defaults(func=cmd_run)

    pl = sub.add_parser("ls", help="list cases")
    add_common(pl, with_only=False)
    pl.set_defaults(func=cmd_ls)

    ps = sub.add_parser("show", help="show a case")
    add_common(ps, with_only=False)
    ps.add_argument("id")
    ps.set_defaults(func=cmd_show)

    pli = sub.add_parser("lint", help="validate suite yaml")
    add_common(pli, with_only=False)
    pli.set_defaults(func=cmd_lint)

    pd = sub.add_parser("diff", help="diff two suites")
    pd.add_argument("--pattern", default="*.y*ml")
    pd.add_argument("a")
    pd.add_argument("b")
    pd.set_defaults(func=cmd_diff)

    pn = sub.add_parser("new", help="scaffold a new case")
    pn.add_argument("--out", required=True)
    pn.add_argument("--id")
    pn.add_argument("--name")
    pn.set_defaults(func=cmd_new)

    pd = sub.add_parser("dryrun", help="dryrun suite with mock plugin (no side effects)")
    add_common(pd)
    pd.add_argument("--concurrency", type=int, default=1)
    pd.add_argument("--junit", help="junit xml path")
    pd.set_defaults(func=cmd_dryrun)

    pps = sub.add_parser("plugin-server", help="start JSON-over-stdio plugin server (for v0.8 gRPC bridge)")
    pps.add_argument("--dryrun", action="store_true")
    pps.set_defaults(func=cmd_plugin_server)

    pr2 = sub.add_parser("results", help="query Result-Store")
    pr2.add_argument("--store", default="aitest-results.db", help="Result-Store SQLite path")
    pr2.add_argument("--case", help="filter by case id")
    pr2.add_argument("--plan", help="filter by plan id")
    pr2.add_argument("--status", help="filter by status (SUCCESS/FAILED/TIMEOUT/...)")
    pr2.add_argument("--limit", type=int, default=20)
    pr2.add_argument("--summary", action="store_true", help="show summary only")
    pr2.set_defaults(func=cmd_results)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
