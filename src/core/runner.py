import subprocess
import time
from typing import Union

class Runner:
    """
    所有命令 / hook / chaos 的统一执行器
    """

    def run(self, cmd: Union[str, list], context: dict, timeout=None):
        """
        cmd: 可以是字符串（shell）或 list（直接 exec）
        """
        start = time.time()

        if isinstance(cmd, str):
            proc = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
        elif isinstance(cmd, list):
            proc = subprocess.run(
                cmd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
        else:
            raise TypeError("cmd must be str or list")

        context["last_stdout"] = proc.stdout
        context["last_stderr"] = proc.stderr
        context["last_returncode"] = proc.returncode
        context["last_duration"] = time.time() - start

        if proc.returncode != 0:
            raise RuntimeError(f"Command failed: {proc.stderr}")

        return proc.stdout
