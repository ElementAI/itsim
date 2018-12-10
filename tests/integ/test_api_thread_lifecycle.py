from typing import Set, Mapping

import pytest

from itsim.machine.api import API
from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management.process import Process
from itsim.simulator import Simulator, advance


Cemetary = Set[str]


def watcher(api: API, cemetary: Cemetary, proc_parent: Process) -> None:
    proc_parent.wait()
    cemetary.add("watcher")


def grandchild(api: API, pid_expected: int, cemetary: Cemetary) -> None:
    assert api.current_process.pid == pid_expected
    advance(20)
    cemetary.add("grandchild")


def elder(api: API, pid_expected: int, cemetary: Cemetary) -> None:
    assert api.current_process.pid == pid_expected
    thread_grandchild = api.run_thread(grandchild, pid_expected, cemetary)
    thread_grandchild.join()
    cemetary.add("elder")


def cadet(api: API, pid_expected: int, cemetary: Cemetary) -> None:
    assert api.current_process.pid == pid_expected
    advance(5)
    cemetary.add("cadet")

def super_long(api: API, pid_expected: int, cemetary: Cemetary) -> None:
    try:
        assert api.current_process.pid == pid_expected
        advance(10000)
        pytest.fail("Supposed to bail out!")
    except ProcessExit:
        raise
    except:
        pytest.fail("Supposed to be killed as the process exits.")
    finally:
        cemetary.add("super_long")


def parent(api: API, cemetary: Cemetary) -> None:
    api.run_proc(watcher, cemetary, api.current_process)
    thread_elder = api.run_thread(elder, api.current_process.pid, cemetary)
    thread_cadet = api.run_thread(cadet, api.current_process.pid, cemetary)
    thread_super_long = api.run_thread(super_long, api.current_process.pid, cemetary)

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
    api.exit()


def test_api_process_lifecycle():
    sim = Simulator()
    cemetary = set()
    Endpoint().with_proc_in(sim, 0, parent, cemetary)
    sim.run()
    assert sim.now() < 200
    assert cemetary == {"parent", "elder", "cadet", "grandchild", "watcher", "super_long"}
