from typing import List

import pytest

from itsim.software.context import Context
from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management.process import Process
from itsim.machine.process_management.thread import ThreadKilled
from itsim.simulator import Simulator, advance
from itsim.types import Timeout


Cemetary = List[str]


DELAY_GRANDCHILD = 20
DELAY_CADET = 5
TIMEOUT_SUPERLONG = 100


def watcher(context: Context, cemetary: Cemetary, proc_parent: Process) -> None:
    proc_parent.wait()
    cemetary.append("watcher")


def grandchild(context: Context, pid_expected: int, cemetary: Cemetary) -> None:
    assert context.process.pid == pid_expected
    advance(DELAY_GRANDCHILD)
    cemetary.append("grandchild")


def elder(context: Context, pid_expected: int, cemetary: Cemetary) -> None:
    assert context.process.pid == pid_expected
    thread_grandchild = context.thread.clone(grandchild, pid_expected, cemetary)
    thread_grandchild.join()
    cemetary.append("elder")


def cadet(context: Context, pid_expected: int, cemetary: Cemetary) -> None:
    assert context.process.pid == pid_expected
    advance(DELAY_CADET)
    cemetary.append("cadet")


def super_long(context: Context, pid_expected: int, cemetary: Cemetary) -> None:
    try:
        assert context.process.pid == pid_expected
        advance(TIMEOUT_SUPERLONG * 10)
        pytest.fail("Supposed to be killed as the process exits.")
    except ThreadKilled:
        raise
    finally:
        cemetary.append("super_long")


def parent(context: Context, cemetary: Cemetary) -> None:
    context.process.fork_exec(watcher, cemetary, context.process)
    thread_elder = context.thread.clone(elder, context.process.pid, cemetary)
    thread_cadet = context.thread.clone(cadet, context.process.pid, cemetary)
    thread_super_long = context.thread.clone(super_long, context.process.pid, cemetary)

    try:
        thread_elder.join()
        thread_cadet.join()
    except Timeout:
        pytest.fail("Not supposed to time out while waiting for these threads.")

    try:
        thread_super_long.join(TIMEOUT_SUPERLONG)
        pytest.fail("Supposed to time out while waiting for super long.")
    except Timeout:
        pass

    cemetary.append("parent")
    context.process.kill()


def test_context_thread_lifecycle():
    sim = Simulator()
    cemetary = []
    Endpoint().with_proc_in(sim, 0, parent, cemetary)
    sim.run()
    assert sim.now() <= TIMEOUT_SUPERLONG + max(DELAY_GRANDCHILD, DELAY_CADET)
    assert cemetary == ["cadet", "grandchild", "elder", "parent", "super_long", "watcher"]
