from typing import Set

import pytest

from itsim.software.context import Context
from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management.process import Process
from itsim.machine.process_management.thread import ThreadKilled
from itsim.simulator import Simulator, advance
from itsim.types import Timeout


Cemetary = Set[str]


def watcher(context: Context, cemetary: Cemetary, proc_parent: Process) -> None:
    proc_parent.wait()
    cemetary.add("watcher")


def grandchild(context: Context, pid_expected: int, cemetary: Cemetary) -> None:
    assert context.process.pid == pid_expected
    advance(20)
    cemetary.add("grandchild")


def elder(context: Context, pid_expected: int, cemetary: Cemetary) -> None:
    assert context.process.pid == pid_expected
    thread_grandchild = context.thread.clone(grandchild, pid_expected, cemetary)
    thread_grandchild.join()
    cemetary.add("elder")


def cadet(context: Context, pid_expected: int, cemetary: Cemetary) -> None:
    assert context.process.pid == pid_expected
    advance(5)
    cemetary.add("cadet")


def super_long(context: Context, pid_expected: int, cemetary: Cemetary) -> None:
    try:
        assert context.process.pid == pid_expected
        advance(10000)
        pytest.fail("Supposed to be killed as the process exits.")
    except ThreadKilled:
        raise
    finally:
        cemetary.add("super_long")


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
        thread_super_long.join(100)
        pytest.fail("Supposed to time out while waiting for super long.")
    except Timeout:
        pass

    cemetary.add("parent")
    context.process.kill()


def test_context_thread_lifecycle():
    sim = Simulator()
    cemetary = set()
    Endpoint().with_proc_in(sim, 0, parent, cemetary)
    sim.run()
    assert sim.now() < 200
    assert cemetary == {"parent", "elder", "cadet", "grandchild", "watcher", "super_long"}
