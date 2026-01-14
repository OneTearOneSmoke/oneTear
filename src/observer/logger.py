# observer/logger.py
import logging
from pathlib import Path
from observer.base import BaseObserver

class LoggerObserver(BaseObserver):
    def __init__(self, base_dir="logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.console = self._console_logger()
        self.file = None

    def _formatter(self):
        return logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

    def _console_logger(self):
        logger = logging.getLogger("console")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(self._formatter())
            logger.addHandler(h)
        return logger

    def _open_file_logger(self, ctx):
        tc_dir = self.base_dir / ctx.testcase.name
        tc_dir.mkdir(parents=True, exist_ok=True)

        log_file = tc_dir / f"{ctx.testcase_id}.log"
        logger = logging.getLogger(ctx.testcase_id)
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(self._formatter())
        logger.addHandler(fh)
        return logger

    # ---------- TestCase ----------
    def testcase_start(self, testcase, ctx):
        self.file = self._open_file_logger(ctx)
        self._log(f"[TESTCASE START] {ctx.testcase_id}", both=True)

    def testcase_end(self, testcase, ctx):
        self._log(f"[TESTCASE END] {ctx.testcase_id}", both=True)
        self._close()

    def testcase_fail(self, testcase, ctx):
        self._log(f"[TESTCASE FAIL] {ctx.testcase_id}", level="error", both=True)
        self._close()

    # ---------- Step ----------
    def step_start(self, step, ctx):
        self._log(f"[STEP START] {ctx.step_id}")
        cmd = step.command.build("do", ctx.vars)
        self._log(f"CMD: {cmd}")

    def step_end(self, step, ctx):
        self._log(f"[STEP END] {ctx.step_id}")
        self._log_result(ctx)

    def step_fail(self, step, ctx):
        self._log(f"[STEP FAIL] {ctx.step_id}", level="error")
        self._log_result(ctx, level="error")

    # ---------- helpers ----------
    def _log(self, msg, level="info", both=False):
        targets = [self.file]
        if both:
            targets.append(self.console)
        for lg in filter(None, targets):
            getattr(lg, level)(msg)

    def _log_result(self, ctx, level="info"):
        if ctx.vars.get("last_stdout"):
            self._log(f"STDOUT:\n{ctx.vars['last_stdout']}", level)
        if ctx.vars.get("last_stderr"):
            self._log(f"STDERR:\n{ctx.vars['last_stderr']}", level)
        self._log(f"RC: {ctx.vars.get('last_returncode')}", level)

    def _close(self):
        if not self.file:
            return
        for h in self.file.handlers:
            h.close()
        self.file.handlers.clear()
        self.file = None
