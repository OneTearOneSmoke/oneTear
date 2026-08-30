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
        # v0.5 ζ: TMRM 集成（可选）—— acquire N 台机器，run 后全部 release
        farm_sessions = []
        farm_store = None
        if getattr(args, "farm", None):
            from .tmrm.allocator import Allocator, AllocateRequest, AllocationError
            from .tmrm.machine import Selector, MachineType
            from .tmrm.store import FarmStore
            farm_store = FarmStore(args.farm)
            allocator = Allocator(farm_store)
            farm_sel = Selector(
                type=MachineType(args.farm_type) if getattr(args, "farm_type", None) else None,
            )
            for slot in range(concurrency):
                try:
                    sess = allocator.acquire(AllocateRequest(
                        owner=getattr(args, "farm_owner", "anon") or "anon",
                        selector=farm_sel,
                        plan_id="run-" + str(uuid.uuid4()),
                    ))
                    farm_sessions.append(sess)
                    print(f"[farm] acquired slot={slot} session={sess.id} machine={sess.machine_id}")
                except AllocationError as e:
                    print(f"[farm] FAIL acquire slot={slot}: {e}")
                    # 释放已分配的
                    for s in farm_sessions:
                        try:
                            allocator.release(s.id)
                        except Exception:  # noqa: BLE001
                            pass
                    farm_store.close()
                    if store is not None:
                        store.close()
                    return 2

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
        if farm_sessions:
            from .tmrm.allocator import Allocator
            allocator2 = Allocator(farm_store)
            for s in farm_sessions:
                try:
                    allocator2.release(s.id)
                    print(f"[farm] released session={s.id} machine={s.machine_id}")
                except Exception as e:  # noqa: BLE001
                    print(f"[farm] release fail session={s.id}: {e}")
            farm_store.close()
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


# ──────────── TRM report handlers ────────────
def cmd_report_flaky(args) -> int:
    from .core.store import ResultStore
    from .trm.flaky import FlakyDetector, FlakyConfig

    store = ResultStore(args.store)
    try:
        det = FlakyDetector(min_ratio=args.min_ratio, max_ratio=args.max_ratio)
        result = det.run(
            store=store,
            plan_id=args.plan,
            config=FlakyConfig(
                window=args.window,
                min_ratio=args.min_ratio,
                max_ratio=args.max_ratio,
            ),
        )
    finally:
        store.close()

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    print(f"[report:flaky] {result.summary}")
    for it in result.data["items"]:
        marker = "FLAKY"
        print(
            f"  {marker}  {it['case_id']:<40s} "
            f"fail={it['failures']}/{it['window']} ({it['fail_ratio']*100:.1f}%) "
            f"last={it['last_status']}"
        )
    for r in result.recommendations:
        print(f"  -> {r}")
    return 0


def cmd_report_baseline(args) -> int:
    from .core.store import ResultStore
    from .trm.baseline import BaselineComparator

    store = ResultStore(args.store)
    try:
        comp = BaselineComparator()
        result = comp.run(
            store=store,
            baseline_plan_id=args.baseline,
            current_plan_id=args.current,
        )
    finally:
        store.close()

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    print(f"[report:baseline] {result.summary}")
    counts = result.data["counts"]
    print(
        f"  new_failure={counts.get('NEW_FAILURE',0)} "
        f"fixed={counts.get('FIXED',0)} "
        f"regression={counts.get('REGRESSION',0)} "
        f"still_fail={counts.get('STILL_FAIL',0)} "
        f"still_pass={counts.get('STILL_PASS',0)} "
        f"new_pass={counts.get('NEW_PASS',0)} "
        f"missing={counts.get('MISSING',0)}"
    )
    for it in result.data["items"]:
        if it["kind"] in ("NEW_FAILURE", "FIXED", "REGRESSION", "MISSING"):
            print(
                f"  {it['kind']:<12s} {it['case_id']:<40s} "
                f"{str(it['baseline_status']):<8s} -> {str(it['current_status'])}"
            )
    return 0


def cmd_report_trend(args) -> int:
    from .core.store import ResultStore
    from .trm.trend import TrendAnalyzer

    store = ResultStore(args.store)
    try:
        ana = TrendAnalyzer()
        result = ana.run(store=store, case_id=args.case, window=args.window)
    finally:
        store.close()

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    print(f"[report:trend] {result.summary}")
    d = result.data
    print(
        f"  window={d['window']} pass_rate={d['pass_rate']:.2%} "
        f"p50={d['duration_p50_ms']}ms p95={d['duration_p95_ms']}ms"
    )
    for r in result.recommendations:
        print(f"  -> {r}")
    return 0


# ──────────── TMRM farm handlers ────────────
def _parse_labels(pairs):
    out = {}
    for kv in pairs or []:
        if "=" not in kv:
            raise SystemExit(f"--label expects key=value, got {kv!r}")
        k, v = kv.split("=", 1)
        out[k] = v
    return out


def cmd_farm_ls(args) -> int:
    from .tmrm.machine import MachineStatus, MachineType
    from .tmrm.store import FarmStore
    store = FarmStore(args.store)
    try:
        ms = MachineStatus(args.status) if args.status else None
        mt = MachineType(args.type) if args.type else None
        rows = store.list_machines(status=ms, machine_type=mt, pool_id=args.pool)
    finally:
        store.close()
    if args.json:
        print(json.dumps([m.to_dict() for m in rows], ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("[farm:ls] 0 machines")
        return 0
    print(f"[farm:ls] {len(rows)} machines")
    for m in rows:
        print(
            f"  {m.id:<40} {m.name:<24} {m.type.value:<10} "
            f"{m.status.value:<12} pool={m.pool_id or '-':<8} provider={m.provider or '-'}"
        )
    return 0


def cmd_farm_register(args) -> int:
    from .tmrm.machine import Machine, MachineType
    from .tmrm.store import FarmStore
    m = Machine(
        id=args.id, name=args.name, type=MachineType(args.type),
        provider=args.provider, region=args.region, zone=args.zone,
        image=args.image, pool_id=args.pool_id, labels=_parse_labels(args.label),
    )
    store = FarmStore(args.store)
    try:
        store.upsert_machine(m)
    finally:
        store.close()
    print(f"[farm:register] ok {m.id} {m.name} ({m.type.value})")
    return 0


def cmd_farm_acquire(args) -> int:
    from .tmrm.machine import MachineType, Selector
    from .tmrm.allocator import Allocator, AllocateRequest, AllocationError
    from .tmrm.store import FarmStore
    sel = Selector(
        type=MachineType(args.type) if args.type else None,
        pool_id=args.pool_id, provider=args.provider, region=args.region,
        labels=_parse_labels(args.label),
    )
    req = AllocateRequest(
        owner=args.owner, selector=sel,
        plan_id=args.plan, task_id=args.task_id, ttl_seconds=args.ttl,
    )
    store = FarmStore(args.store)
    try:
        a = Allocator(store)
        sess = a.acquire(req)
    except AllocationError as e:
        store.close()
        print(f"[farm:acquire] FAIL {e}")
        return 2
    finally:
        store.close()
    if args.json:
        print(json.dumps(sess.to_dict(), ensure_ascii=False, indent=2))
        return 0
    print(
        f"[farm:acquire] ok session={sess.id} machine={sess.machine_id} "
        f"owner={sess.owner} ttl={sess.ttl_seconds}"
    )
    return 0


def cmd_farm_release(args) -> int:
    from .tmrm.allocator import Allocator, AllocationError
    from .tmrm.store import FarmStore
    store = FarmStore(args.store)
    try:
        a = Allocator(store)
        sess = a.release(args.session)
    except AllocationError as e:
        store.close()
        print(f"[farm:release] FAIL {e}")
        return 2
    finally:
        store.close()
    if args.json:
        print(json.dumps(sess.to_dict(), ensure_ascii=False, indent=2))
        return 0
    print(
        f"[farm:release] ok session={sess.id} machine={sess.machine_id} "
        f"released_at={sess.released_at:.0f}"
    )
    return 0


def cmd_farm_heartbeat(args) -> int:
    from .tmrm.health import HealthChecker
    from .tmrm.store import FarmStore
    store = FarmStore(args.store)
    try:
        hc = HealthChecker(store)
        m = hc.heartbeat(args.machine)
    finally:
        store.close()
    print(f"[farm:heartbeat] ok {m.id} last_heartbeat={m.last_heartbeat:.0f}")
    return 0


def cmd_farm_health_check(args) -> int:
    from .tmrm.health import HealthChecker
    from .tmrm.store import FarmStore
    store = FarmStore(args.store)
    try:
        hc = HealthChecker(store)
        rec = hc.check_one(args.machine)
    finally:
        store.close()
    if args.json:
        print(json.dumps(rec.to_dict(), ensure_ascii=False, indent=2))
        return 0
    print(
        f"[farm:health-check] {args.machine} status={rec.status.value} "
        f"latency={rec.latency_ms}ms error={rec.error!r}"
    )
    return 0


def cmd_farm_sweep(args) -> int:
    from .tmrm.health import HealthChecker
    from .tmrm.store import FarmStore
    store = FarmStore(args.store)
    try:
        hc = HealthChecker(store)
        recs = hc.sweep()
    finally:
        store.close()
    if args.json:
        print(json.dumps([r.to_dict() for r in recs], ensure_ascii=False, indent=2))
        return 0
    bad = [r for r in recs if r.status.value != "ok"]
    print(f"[farm:sweep] {len(recs)} checked, {len(bad)} unhealthy/degraded")
    for r in bad:
        print(f"  {r.machine_id:<40} {r.status.value:<10} {r.error}")
    return 0


def cmd_farm_sessions(args) -> int:
    from .tmrm.session import SessionStatus
    from .tmrm.store import FarmStore
    store = FarmStore(args.store)
    try:
        ss = SessionStatus(args.status) if args.status else None
        rows = store.list_sessions(owner=args.owner, status=ss)
    finally:
        store.close()
    if args.json:
        print(json.dumps([s.to_dict() for s in rows], ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("[farm:sessions] 0")
        return 0
    print(f"[farm:sessions] {len(rows)}")
    for s in rows:
        print(
            f"  {s.id:<40} machine={s.machine_id:<24} owner={s.owner:<16} "
            f"status={s.status.value:<10} plan={s.plan_id or '-':<8}"
        )
    return 0


# ──────────── TCM case handlers ────────────
def cmd_case_lifecycle(args) -> int:
    """查询 / 修改 case 生命周期。

    设计：状态机本身只校验合法性 + 给告警；当前版本不写回 YAML（v1.0 接 GitOps 后落库）。
    """
    from .tcm.lifecycle import LifecycleStatus, IllegalTransition, allowed_next, can_run
    from .tcm.suite import Suite
    from .tcm.case import Case

    suite = Suite.load_dir(args.suite, pattern=args.pattern)
    target_ids = {args.id} if args.id else None
    rows = []
    for c in suite.cases:
        if target_ids and c.id not in target_ids:
            continue
        # 当前 lifecycle = 从 YAML 读不到，沿用"未指定 → ACTIVE"
        cur = LifecycleStatus.ACTIVE
        row = {
            "id": c.id,
            "current": cur.value,
            "next": [s.value for s in allowed_next(cur)],
            "can_run": can_run(cur),
        }
        if args.to:
            try:
                from .tcm.lifecycle import transition as lc_transition
                new = lc_transition(cur, LifecycleStatus(args.to))
                row["target"] = new.value
            except IllegalTransition as e:
                row["error"] = str(e)
        rows.append(row)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("[case:lifecycle] 0 cases matched")
        return 0
    print(f"[case:lifecycle] {len(rows)} cases")
    for r in rows:
        line = f"  {r['id']:<40} current={r['current']:<10} next={','.join(r['next']):<24} can_run={r['can_run']}"
        if "target" in r:
            line += f" -> {r['target']}"
        if "error" in r:
            line += f"  ERR={r['error']}"
        print(line)
    return 0


def cmd_case_diff(args) -> int:
    from .tcm.suite import Suite
    from .tcm.diff import diff_suites

    sa = Suite.load_dir(args.a, pattern=args.pattern)
    sb = Suite.load_dir(args.b, pattern=args.pattern)
    diffs = diff_suites(sa, sb)
    if args.json:
        print(json.dumps([d.to_dict() for d in diffs], ensure_ascii=False, indent=2))
        return 0
    changed = [d for d in diffs if not d.identical]
    print(f"[case:diff] {len(diffs)} cases compared, {len(changed)} changed")
    for d in changed:
        print(f"  {d.case_id}:")
        for f, (ov, nv) in d.meta.items():
            print(f"    meta.{f}: {ov!r} -> {nv!r}")
        for s in d.steps:
            print(f"    steps.{s.field} ({s.kind}): {s.note}")
    return 0


def cmd_case_version(args) -> int:
    from .tcm.suite import Suite
    from .tcm.version import CaseVersion, content_hash, bump_semver

    suite = Suite.load_dir(args.suite, pattern=args.pattern)
    target_ids = {args.id} if args.id else None
    rows = []
    for c in suite.cases:
        if target_ids and c.id not in target_ids:
            continue
        cv = CaseVersion.from_dict(c.to_dict())
        row = {
            "id": c.id,
            "semver": cv.semver,
            "content_hash": cv.content_hash,
            "version": str(cv),
        }
        if args.bump:
            row["bumped"] = bump_semver(cv.semver, args.bump)
        rows.append(row)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("[case:version] 0 cases matched")
        return 0
    print(f"[case:version] {len(rows)} cases")
    for r in rows:
        line = f"  {r['id']:<40} {r['version']}"
        if "bumped" in r:
            line += f"  -> bumped: {r['bumped']}"
        print(line)
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
    pr.add_argument("--farm", help="TMRM farm SQLite path (acquire machines from Test Farm)")
    pr.add_argument("--farm-type", dest="farm_type",
                    choices=["host", "browser", "mobile", "desktop", "sandbox"],
                    help="TMRM 申请的机器类型")
    pr.add_argument("--farm-owner", dest="farm_owner", default="anon",
                    help="TMRM 申请机器的 owner (team / user)")
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

    # ──────── TRM: report 子命令（flaky / baseline / trend）────────
    preport = sub.add_parser("report", help="TRM 高阶分析：flaky / baseline / trend")
    preport_sub = preport.add_subparsers(dest="report_cmd", required=True)

    prf = preport_sub.add_parser("flaky", help="列出 flaky case")
    prf.add_argument("--store", default="aitest-results.db")
    prf.add_argument("--plan", help="按 plan_id 过滤")
    prf.add_argument("--window", type=int, default=50)
    prf.add_argument("--min-ratio", type=float, default=0.05)
    prf.add_argument("--max-ratio", type=float, default=0.50)
    prf.add_argument("--json", action="store_true", help="输出 JSON")
    prf.set_defaults(func=cmd_report_flaky)

    prb = preport_sub.add_parser("baseline", help="对比基线 vs 当前 run")
    prb.add_argument("--store", default="aitest-results.db")
    prb.add_argument("--baseline", required=True, help="基线 plan_id")
    prb.add_argument("--current", required=True, help="当前 plan_id")
    prb.add_argument("--json", action="store_true")
    prb.set_defaults(func=cmd_report_baseline)

    prt = preport_sub.add_parser("trend", help="单 case 趋势")
    prt.add_argument("--store", default="aitest-results.db")
    prt.add_argument("--case", required=True)
    prt.add_argument("--window", type=int, default=50)
    prt.add_argument("--json", action="store_true")
    prt.set_defaults(func=cmd_report_trend)

    # ──────────── TMRM: farm 子命令（机器注册 / 分配 / 健康） ────────────
    pfm = sub.add_parser("farm", help="TMRM 机器 / 资源池 / 分配")
    pfm_sub = pfm.add_subparsers(dest="farm_cmd", required=True)

    pfml = pfm_sub.add_parser("ls", help="列出机器")
    pfml.add_argument("--store", default="aitest-farm.db")
    pfml.add_argument("--status", choices=["available", "allocated", "maintenance", "retired", "unhealthy"])
    pfml.add_argument("--type", choices=["host", "browser", "mobile", "desktop", "sandbox"])
    pfml.add_argument("--pool", help="按 pool_id 过滤")
    pfml.add_argument("--json", action="store_true")
    pfml.set_defaults(func=cmd_farm_ls)

    pfmr = pfm_sub.add_parser("register", help="注册一台机器")
    pfmr.add_argument("--store", default="aitest-farm.db")
    pfmr.add_argument("--id", required=True)
    pfmr.add_argument("--name", required=True)
    pfmr.add_argument("--type", required=True, choices=["host", "browser", "mobile", "desktop", "sandbox"])
    pfmr.add_argument("--provider")
    pfmr.add_argument("--region")
    pfmr.add_argument("--zone")
    pfmr.add_argument("--image")
    pfmr.add_argument("--pool", dest="pool_id")
    pfmr.add_argument("--label", action="append", default=[], help="key=value (可重复)")
    pfmr.set_defaults(func=cmd_farm_register)

    pfma = pfm_sub.add_parser("acquire", help="分配一台机器")
    pfma.add_argument("--store", default="aitest-farm.db")
    pfma.add_argument("--owner", required=True, help="团队 / 用户")
    pfma.add_argument("--type", choices=["host", "browser", "mobile", "desktop", "sandbox"])
    pfma.add_argument("--pool", dest="pool_id")
    pfma.add_argument("--provider")
    pfma.add_argument("--region")
    pfma.add_argument("--label", action="append", default=[], help="key=value")
    pfma.add_argument("--plan", help="plan_id")
    pfma.add_argument("--task", dest="task_id", help="task_id")
    pfma.add_argument("--ttl", type=float, help="TTL (秒)")
    pfma.add_argument("--json", action="store_true")
    pfma.set_defaults(func=cmd_farm_acquire)

    pfmr = pfm_sub.add_parser("release", help="释放一台机器")
    pfmr.add_argument("--store", default="aitest-farm.db")
    pfmr.add_argument("--session", required=True)
    pfmr.add_argument("--json", action="store_true")
    pfmr.set_defaults(func=cmd_farm_release)

    pfmh = pfm_sub.add_parser("heartbeat", help="心跳更新")
    pfmh.add_argument("--store", default="aitest-farm.db")
    pfmh.add_argument("--machine", required=True)
    pfmh.set_defaults(func=cmd_farm_heartbeat)

    pfmc = pfm_sub.add_parser("health-check", help="对一台机器跑健康检查")
    pfmc.add_argument("--store", default="aitest-farm.db")
    pfmc.add_argument("--machine", required=True)
    pfmc.add_argument("--json", action="store_true")
    pfmc.set_defaults(func=cmd_farm_health_check)

    pfms = pfm_sub.add_parser("sweep", help="扫所有机器，更新健康状态")
    pfms.add_argument("--store", default="aitest-farm.db")
    pfms.add_argument("--json", action="store_true")
    pfms.set_defaults(func=cmd_farm_sweep)

    pfmt = pfm_sub.add_parser("sessions", help="列出 sessions")
    pfmt.add_argument("--store", default="aitest-farm.db")
    pfmt.add_argument("--owner")
    pfmt.add_argument("--status", choices=["acquired", "released", "expired", "failed"])
    pfmt.add_argument("--json", action="store_true")
    pfmt.set_defaults(func=cmd_farm_sessions)

    # ──────────── TCM: case 子命令（lifecycle / diff / version） ────────────
    pc = sub.add_parser("case", help="TCM 用例管理（lifecycle / diff / version）")
    pc_sub = pc.add_subparsers(dest="case_cmd", required=True)

    pcl = pc_sub.add_parser("lifecycle", help="查询或修改用例生命周期")
    pcl.add_argument("--suite", default="cases")
    pcl.add_argument("--pattern", default="*.y*ml")
    pcl.add_argument("--id", help="只对指定 case id 操作")
    pcl.add_argument("--to", choices=["draft", "active", "deprecated", "retired"],
                     help="把 case 转到的目标状态")
    pcl.add_argument("--json", action="store_true")
    pcl.set_defaults(func=cmd_case_lifecycle)

    pcd = pc_sub.add_parser("diff", help="对比两 suite 的语义 diff")
    pcd.add_argument("--a", required=True, help="A suite 路径（文件或目录）")
    pcd.add_argument("--b", required=True, help="B suite 路径（文件或目录）")
    pcd.add_argument("--pattern", default="*.y*ml")
    pcd.add_argument("--json", action="store_true")
    pcd.set_defaults(func=cmd_case_diff)

    pcv = pc_sub.add_parser("version", help="计算 case 的 semver + content hash")
    pcv.add_argument("--suite", default="cases")
    pcv.add_argument("--pattern", default="*.y*ml")
    pcv.add_argument("--id", help="只看这一个 case")
    pcv.add_argument("--bump", choices=["major", "minor", "patch"],
                     help="自动 bump 当前 semver（仅展示，不写回）")
    pcv.add_argument("--current", default="1.0.0", help="当前 semver")
    pcv.add_argument("--json", action="store_true")
    pcv.set_defaults(func=cmd_case_version)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
