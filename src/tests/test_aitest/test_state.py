import pytest

from aitest.core.state import (
    Status, IllegalTransition, transition, can_transition,
    is_pass, is_fail, is_terminal, to_ok,
)


def test_terminal_statuses():
    for s in (Status.SUCCESS, Status.FAILED, Status.TIMEOUT,
              Status.CANCELED, Status.BLOCKED, Status.ERROR):
        assert is_terminal(s)
    for s in (Status.PENDING, Status.QUEUED, Status.DISPATCHED, Status.RUNNING):
        assert not is_terminal(s)


def test_pass_and_fail_sets():
    assert is_pass(Status.SUCCESS)
    assert not is_pass(Status.FAILED)
    assert is_fail(Status.FAILED)
    assert is_fail(Status.TIMEOUT)
    assert is_fail(Status.ERROR)
    assert not is_fail(Status.SUCCESS)
    assert not is_fail(Status.CANCELED)
    assert not is_fail(Status.BLOCKED)


def test_to_ok():
    assert to_ok(Status.SUCCESS) is True
    for s in (Status.FAILED, Status.TIMEOUT, Status.CANCELED,
              Status.BLOCKED, Status.ERROR, Status.RUNNING):
        assert to_ok(s) is False


def test_legal_transitions():
    assert can_transition(Status.PENDING, Status.QUEUED)
    assert can_transition(Status.QUEUED, Status.DISPATCHED)
    assert can_transition(Status.DISPATCHED, Status.RUNNING)
    assert can_transition(Status.RUNNING, Status.SUCCESS)
    assert can_transition(Status.RUNNING, Status.FAILED)
    assert can_transition(Status.RUNNING, Status.TIMEOUT)
    assert can_transition(Status.RUNNING, Status.CANCELED)


def test_blocked_can_come_from_any_non_terminal():
    for s in (Status.PENDING, Status.QUEUED, Status.DISPATCHED, Status.RUNNING):
        assert can_transition(s, Status.BLOCKED)


def test_terminal_cannot_transition():
    for src in (Status.SUCCESS, Status.FAILED, Status.TIMEOUT,
                Status.CANCELED, Status.BLOCKED, Status.ERROR):
        for dst in Status:
            assert not can_transition(src, dst), f"{src} -> {dst} should be illegal"


def test_illegal_transition_raises():
    with pytest.raises(IllegalTransition):
        transition(Status.PENDING, Status.SUCCESS)
    with pytest.raises(IllegalTransition):
        transition(Status.RUNNING, Status.PENDING)


def test_transition_returns_dst():
    assert transition(Status.PENDING, Status.QUEUED) == Status.QUEUED
