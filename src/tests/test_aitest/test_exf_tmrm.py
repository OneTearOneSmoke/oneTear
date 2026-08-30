"""EXF ↔ TMRM 集成测试：aitest run --farm 链路。"""
from __future__ import annotations
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from aitest.tmrm.machine import Machine, MachineStatus, MachineType
from aitest.tmrm.store import FarmStore


@pytest.fixture
def farm_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


@pytest.fixture
def store_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


@pytest.fixture
def suite_dir(tmp_path):
    """极简套件：单个 PASS case。"""
    d = tmp_path / "suite"
    d.mkdir()
    (d / "x.yaml").write_text(
        "id: ai.demo\n"
        "tags: [smoke]\n"
        "run:\n"
        "  cmd: shell.run\n"
        "  args:\n"
        "    cmd: echo hi\n"
        "asserts:\n"
        "  - contains: hi\n",
        encoding="utf-8",
    )
    return str(d)


def _seed_machines(farm_path: str, n: int) -> None:
    store = FarmStore(farm_path)
    for i in range(n):
        m = Machine(
            id=f"host-{i}", name=f"ci-{i}",
            type=MachineType.HOST, status=MachineStatus.AVAILABLE,
        )
        store.upsert_machine(m)
    store.close()


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """直接调 aitest CLI（spawn 子进程，避免与 sqlite 句柄冲突）。"""
    cmd = [sys.executable, "-m", "aitest", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


def test_run_with_farm_acquires_and_releases(farm_path, store_path, suite_dir):
    _seed_machines(farm_path, 2)
    p = _run_cli(
        "run",
        "--suite", suite_dir,
        "--farm", farm_path,
        "--farm-type", "host",
        "--farm-owner", "teamA",
        "--concurrency", "2",
        "--store", store_path,
    )
    assert p.returncode == 0, f"stdout={p.stdout}\nstderr={p.stderr}"
    # acquire + release 都应出现
    assert "[farm] acquired" in p.stdout
    assert "[farm] released" in p.stdout

    # 机器全回到 available，session 全 released
    farm = FarmStore(farm_path)
    try:
        ms = farm.list_machines()
        assert all(m.status == MachineStatus.AVAILABLE for m in ms)
        ss = farm.list_sessions(owner="teamA")
        assert all(s.status.value == "released" for s in ss)
    finally:
        farm.close()


def test_run_with_farm_no_match_fails(farm_path, store_path, suite_dir):
    # 没有任何 machine 时 acquire 应失败 → run 退出 2
    p = _run_cli(
        "run",
        "--suite", suite_dir,
        "--farm", farm_path,
        "--farm-type", "host",
        "--concurrency", "1",
        "--store", store_path,
    )
    assert p.returncode == 2
    assert "[farm] FAIL acquire" in p.stdout


def test_run_without_farm_unchanged(store_path, suite_dir):
    """不带 --farm 时，TMRM 不应被读 / 写。"""
    p = _run_cli(
        "run",
        "--suite", suite_dir,
        "--store", store_path,
    )
    assert p.returncode == 0, f"stderr={p.stderr}"
    assert "[farm]" not in p.stdout


def test_run_with_farm_persists_sessions(farm_path, store_path, suite_dir):
    _seed_machines(farm_path, 1)
    p = _run_cli(
        "run",
        "--suite", suite_dir,
        "--farm", farm_path,
        "--farm-type", "host",
        "--concurrency", "1",
        "--store", store_path,
    )
    assert p.returncode == 0

    farm = FarmStore(farm_path)
    try:
        sessions = farm.list_sessions()
        assert len(sessions) == 1
        s = sessions[0]
        assert s.owner == "anon"  # 默认值
        assert s.status.value == "released"
        assert s.plan_id and s.plan_id.startswith("run-")
    finally:
        farm.close()
