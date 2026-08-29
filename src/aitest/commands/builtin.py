"""内置夹具命令。"""
import random
import shutil
import tempfile
from pathlib import Path

from ..core.errors import CommandFailure


class SeedRng:
    name = "builtin.seed_rng"

    def run(self, args, ctx):
        random.seed(args.get("seed", 0))
        ctx.meta["rng_seeded"] = True
        return {"seed": args.get("seed", 0)}


class MakeTmp:
    name = "builtin.make_tmp"

    def run(self, args, ctx):
        d = Path(tempfile.mkdtemp(prefix=args.get("prefix", "aitest_")))
        ctx.meta["tmp"] = str(d)
        return {"tmp": str(d)}


class CleanTmp:
    name = "builtin.clean_tmp"

    def run(self, args, ctx):
        base = args.get("base") or ctx.meta.get("tmp") or tempfile.gettempdir()
        pat = args.get("pattern", "aitest_*")
        removed = 0
        for p in Path(base).glob(pat):
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
                removed += 1
            except Exception:
                pass
        return {"removed": removed}


class Sleep:
    name = "builtin.sleep"

    def run(self, args, ctx):
        import time
        time.sleep(float(args.get("seconds", 0)))
        return {"slept": float(args.get("seconds", 0))}
