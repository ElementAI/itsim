from typing import Set, Mapping

import pytest

from itsim.machine.dashboard import Dashboard
from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management.process import Process
from itsim.simulator import Simulator, advance


Cemetary = Set[str]


def watcher(d: Dashboard, cemetary: Cemetary, proc_parent: Process) -> None:
    proc_parent.wait()
    cemetary.add("watcher")


def grandchild(d: Dashboard, pid_expected: int, cemetary: Cemetary) -> None:
    assert d.current_process.pid == pid_expected
    advance(20)
    cemetary.add("grandchild")


def elder(d: Dashboard, pid_expected: int, cemetary: Cemetary) -> None:
    assert d.current_process.pid == pid_expected
    thread_grandchild = d.run_thread(grandchild, pid_expected, cemetary)
    thread_grandchild.join()
    cemetary.add("elder")


def cadet(d: Dashboard, pid_expected: int, cemetary: Cemetary) -> None:
    assert d.current_process.pid == pid_expected
    advance(5)
    cemetary.add("cadet")


def super_long(d: Dashboard, pid_expected: int, cemetary: Cemetary) -> None:
    try:
        assert d.current_process.pid == pid_expected
        advance(10000)
        pytest.fail("Supposed to bail out!")
    except ProcessExit:
        raise
    except:
        pytest.fail("Supposed to be killed as the process exits.")
    finally:
        cemetary.add("super_long")


def parent(d: Dashboard, cemetary: Cemetary) -> None:
    d.run_proc(watcher, cemetary, d.current_process)
    thread_elder = d.run_thread(elder, d.current_process.pid, cemetary)
    thread_cadet = d.run_thread(cadet, d.current_process.pid, cemetary)
    thread_super_long = d.run_thread(super_long, d.current_process.pid, cemetary)

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


def test_dashboard_process_lifecycle():
    sim = Simulator()
    cemetary = set()
    Endpoint().with_proc_in(sim, 0, parent, cemetary)
    sim.run()
    assert sim.now() < 200
    assert cemetary == {"parent", "elder", "cadet", "grandchild", "watcher", "super_long"}
