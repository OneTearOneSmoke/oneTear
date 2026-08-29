import os
import sys
import subprocess
import tempfile
import textwrap
from pathlib import Path


def _run_aitest(*args, cwd: str | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "aitest", *args]
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd or os.getcwd()
    )


def test_cli_lint_ok(tmp_path):
    (tmp_path / "a.yaml").write_text("id: a\n", encoding="utf-8")
    src = Path(__file__).resolve().parents[2]
    p = subprocess.run(
        [sys.executable, "-m", "aitest", "lint", "--suite", str(tmp_path)],
        capture_output=True, text=True, cwd=str(src),
    )
    assert p.returncode == 0, p.stderr
    assert "1 cases" in p.stdout


def test_cli_ls(tmp_path):
    (tmp_path / "a.yaml").write_text("id: a\ntags: [t1]\n", encoding="utf-8")
    src = Path(__file__).resolve().parents[2]
    p = subprocess.run(
        [sys.executable, "-m", "aitest", "ls", "--suite", str(tmp_path)],
        capture_output=True, text=True, cwd=str(src),
    )
    assert p.returncode == 0, p.stderr
    assert "a" in p.stdout
