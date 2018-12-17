from typing import Set

import pytest

from itsim.software.context import Context
from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management.process import Process
from itsim.machine.process_management.thread import ThreadKilled
from itsim.simulator import Simulator, advance
from itsim.types import Timeout


Cemetary = Set[str]


def watcher(d: Context, cemetary: Cemetary, proc_parent: Process) -> None:
    proc_parent.wait()
    cemetary.add("watcher")


def grandchild(d: Context, pid_expected: int, cemetary: Cemetary) -> None:
    assert d.process.pid == pid_expected
    advance(20)
    cemetary.add("grandchild")


def elder(d: Context, pid_expected: int, cemetary: Cemetary) -> None:
    assert d.process.pid == pid_expected
    thread_grandchild = d.run_thread(grandchild, pid_expected, cemetary)
    thread_grandchild.join()
    cemetary.add("elder")


def cadet(d: Context, pid_expected: int, cemetary: Cemetary) -> None:
    assert d.process.pid == pid_expected
    advance(5)
    cemetary.add("cadet")


def super_long(d: Context, pid_expected: int, cemetary: Cemetary) -> None:
    try:
        assert d.process.pid == pid_expected
        advance(10000)
        pytest.fail("Supposed to be killed as the process exits.")
    except ThreadKilled:
        raise
    finally:
        cemetary.add("super_long")


def parent(d: Context, cemetary: Cemetary) -> None:
    d.run_proc(watcher, cemetary, d.process)
    thread_elder = d.run_thread(elder, d.process.pid, cemetary)
    thread_cadet = d.run_thread(cadet, d.process.pid, cemetary)
    thread_super_long = d.run_thread(super_long, d.process.pid, cemetary)

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
    d.exit()


def test_context_thread_lifecycle():
    sim = Simulator()
    cemetary = set()
    Endpoint().with_proc_in(sim, 0, parent, cemetary)
    sim.run()
    assert sim.now() < 200
    assert cemetary == {"parent", "elder", "cadet", "grandchild", "watcher", "super_long"}
