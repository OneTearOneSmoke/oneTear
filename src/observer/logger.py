import logging
from pathlib import Path
import json
import textwrap
from observer.base import BaseObserver

MAX_OUTPUT_LEN = 2000  # stdout/stderr 最大打印长度


class LoggerObserver(BaseObserver):
    def __init__(self, base_dir="logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    # =========================
    # Testcase level
    # =========================

    def _setup_logger(self, testcase):
        logger = logging.getLogger(f"testcase.{testcase.name}")
        logger.setLevel(logging.INFO)
        if logger.handlers:
            logger.handlers.clear()
        fh = logging.FileHandler(
            self.base_dir / f"{testcase.name}.log", encoding="utf-8"
        )
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
        self.logger = logger

    def testcase_start(self, testcase, context):
        self._setup_logger(testcase)
        self.logger.info("=" * 80)
        self.logger.info("TESTCASE START")
        self.logger.info(f"name    : {testcase.name}")
        self.logger.info(f"context : {json.dumps(context, ensure_ascii=False)}")
        self.logger.info("=" * 80)

    def testcase_end(self, testcase, context, success):
        self.logger.info("-" * 80)
        self.logger.info(
            f"TESTCASE END success={success} "
            f"context={json.dumps(context, ensure_ascii=False)}"
        )
        self.logger.info("-" * 80)

    def testcase_error(self, testcase, context, error):
        self.logger.error("TESTCASE ERROR")
        self.logger.exception(error)

    # =========================
    # Step level
    # =========================

    def step_start(self, testcase, node, context):
        self.logger.info("")
        self.logger.info(f"[STEP START] {getattr(node, 'name', repr(node))}")

        node_type = node.type
        self.logger.info(f"  type    : {node_type}")
        self.logger.info(f"  context : {json.dumps(context, ensure_ascii=False)}")

        # 尝试打印模板命令
        cmd_template = node.executor.build(node.cmd_template, context)
        if cmd_template:
            self.logger.info("  template command :")
            self.logger.info(textwrap.indent(str(cmd_template).strip(), "    "))

        args = getattr(node, "args", None)
        if args:
            self.logger.info(f"  args    : {json.dumps(args, ensure_ascii=False)}")

    def step_end(self, testcase, node, context, result):
        self.logger.info(f"[STEP END] {getattr(node, 'name', repr(node))}")

        rc = result.get("rc") if result else None
        duration = result.get("duration_ms") if result else None
        self.logger.info(f"  rc      : {rc}")
        self.logger.info(f"  duration: {duration} ms" if duration else "")

        # 关键改进：打印执行后的命令
        executed_cmd = result.get("cmd_executed") if result else None
        if executed_cmd:
            self.logger.info("  executed command :")
            self.logger.info(textwrap.indent(str(executed_cmd).strip(), "    "))

        self._log_output("stdout", result.get("stdout") if result else None)
        self._log_output("stderr", result.get("stderr") if result else None)

    def step_error(self, testcase, node, context, error, result=None):
        self.logger.error(f"[STEP ERROR] {getattr(node, 'name', repr(node))}")
        self.logger.exception(error)

        if result:
            self.logger.error("  Partial result:")
            executed_cmd = result.get("cmd_executed")
            if executed_cmd:
                self.logger.error("  executed command :")
                self.logger.error(textwrap.indent(str(executed_cmd).strip(), "    "))

            self._log_output("stdout", result.get("stdout"))
            self._log_output("stderr", result.get("stderr"))

    # =========================
    # Helpers
    # =========================

    def _log_output(self, name, content):
        if not content:
            return

        content = str(content)
        truncated = False
        if len(content) > MAX_OUTPUT_LEN:
            content = content[:MAX_OUTPUT_LEN]
            truncated = True

        self.logger.info(f"  {name}:")
        self.logger.info(textwrap.indent(content.rstrip(), "    "))

        if truncated:
            self.logger.info(f"    ... ({name} truncated)")
