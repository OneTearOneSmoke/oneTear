import logging
from pathlib import Path
import json
import textwrap
from observer.base import BaseObserver

MAX_OUTPUT_LEN = 2000

class LoggerObserver(BaseObserver):
    def __init__(self, base_dir="logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.logger = None

    def _setup_logger(self, testcase):
        logger = logging.getLogger(f"testcase.{testcase.name}")
        logger.setLevel(logging.INFO)
        if logger.handlers:
            logger.handlers.clear()
        fh = logging.FileHandler(self.base_dir / f"{testcase.name}.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
        self.logger = logger

    def testcase_start(self, testcase, context):
        self._setup_logger(testcase)
        self.logger.info("="*80)
        self.logger.info("TESTCASE START")
        self.logger.info(f"name    : {testcase.name}")
        self.logger.info(f"context : {json.dumps(context, ensure_ascii=False)}")
        self.logger.info("="*80)

    def testcase_end(self, testcase, context, success):
        self.logger.info("-"*80)
        self.logger.info(f"TESTCASE END success={success}")
        self.logger.info("-"*80)

    def testcase_error(self, testcase, context, error):
        self.logger.error("TESTCASE ERROR")
        self.logger.exception(error)

    # =========================
    # Step
    # =========================
    def step_start(self, testcase, node, context):
        self.logger.info(f"[STEP START] {getattr(node, 'name', repr(node))}")
        self.logger.info(f"  cmd_ref : {getattr(node, 'cmd_ref', getattr(node,'name',''))}")
        self.logger.info(f"  expect  : {json.dumps(getattr(node,'expect',{}), ensure_ascii=False)}")
        self.logger.info(f"  context : {json.dumps(context, ensure_ascii=False)}")

    def step_end(self, testcase, node, context, result):
        self.logger.info(f"[STEP END] {getattr(node, 'name', repr(node))}")
        if result:
            self.logger.info(f"  rc      : {result.get('rc')}")
            self.logger.info(f"  stdout  : {result.get('stdout')}")
            self.logger.info(f"  stderr  : {result.get('stderr')}")

    def step_error(self, testcase, node, context, error, result=None):
        self.logger.error(f"[STEP ERROR] {getattr(node, 'name', repr(node))}")
        self.logger.exception(error)
        if result:
            self.logger.error(f"  Partial result: {json.dumps(result, ensure_ascii=False)}")

    # =========================
    # Hook
    # =========================
    def hook_start(self, testcase, hook, context):
        self.logger.info(f"[HOOK START] {hook.name}")

    def hook_end(self, testcase, hook, context, result):
        self.logger.info(f"[HOOK END] {hook.name}")
        if result:
            self.logger.info(f"  rc      : {result.get('rc')}")
            self.logger.info(f"  stdout  : {result.get('stdout')}")
            self.logger.info(f"  stderr  : {result.get('stderr')}")

    def hook_error(self, testcase, hook, context, error, result=None):
        self.logger.error(f"[HOOK ERROR] {hook.name}")
        self.logger.exception(error)
        if result:
            self.logger.error(f"  Partial result: {json.dumps(result, ensure_ascii=False)}")
