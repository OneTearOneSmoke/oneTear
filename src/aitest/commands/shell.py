"""shell.run —— 执行 shell 命令。"""
import subprocess

from ..core.errors import CommandFailure


class ShellRun:
    name = "shell.run"

    def run(self, args, ctx):
        cmd = args.get("cmd")
        if not cmd:
            raise CommandFailure(self.name, "missing args.cmd")
        timeout = args.get("timeout")
        try:
            p = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise CommandFailure(self.name, f"timeout after {timeout}s")
        out = {"stdout": p.stdout, "stderr": p.stderr, "rc": p.returncode}
        if args.get("fail_on_nonzero", True) and p.returncode != 0:
            raise CommandFailure(self.name, f"rc={p.returncode} stderr={p.stderr[:200]}")
        return out
