import logging
from pathlib import Path
from observer.base import BaseObserver

class LoggerObserver(BaseObserver):
    def __init__(self, base_dir="logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def _setup_logger(self, testcase):
        self.logger = logging.getLogger(testcase.name)
        self.logger.setLevel(logging.INFO)
        fh = logging.FileHandler(self.base_dir / f"{testcase.name}.log")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.handlers = [fh]

    def testcase_start(self, testcase, context):
        self._setup_logger(testcase)
        self.logger.info(f"TESTCASE START context={context}")

    def step_start(self, testcase, node, context):
        self.logger.info(f"[{node.name}] START context={context}")

    def step_end(self, testcase, node, context, result):
        self.logger.info(f"[{node.name}] END rc={result['rc']} stdout={result['stdout']} stderr={result['stderr']}")

    def testcase_error(self, testcase, context, error):
        self.logger.error(f"ERROR: {error}")

    def testcase_end(self, testcase, context, success):
        self.logger.info(f"TESTCASE END success={success}")
