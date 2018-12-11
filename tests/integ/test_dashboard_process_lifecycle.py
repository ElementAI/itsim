from typing import Set, Mapping

import pytest

from itsim.machine.dashboard import Dashboard
from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management.process import Process
from itsim.simulator import Simulator, advance


Cemetary = Set[str]
Name2Child = Mapping[str, Process]


def cain(d: Dashboard, cemetary: Cemetary, child: Name2Child):
    advance(130)
    assert d.current_process == child["cain"]
    child["abel"].kill()
    advance(730 - 130)
    cemetary.add("cain")


def abel(d: Dashboard, cemetary: Cemetary, child: Name2Child):
    assert d.current_process == child["abel"]
    try:
        advance(1000)
    finally:
        cemetary.add("abel")


def seth(d: Dashboard, cemetary: Cemetary, child: Name2Child):
    assert d.current_process == child["seth"]
    advance(912)
    cemetary.add("seth")


def adameve(d: Dashboard, cemetary: Cemetary):
    child: Name2Child = {}
    for name, moment in [(cain, 0), (abel, 0), (seth, 122)]:
        child[name] = d.run_proc_in(moment, name, cemetary, child)

    for name_expected, moment in [("abel", 130), ("cain", 730), ("seth", 130 + 912)]:
        proc_dead = d.wait_proc()
        assert d.now() == pytest.approx(moment)
        for name, proc in child.items():
            if proc.pid == proc_dead.pid:
                assert name == name_expected
                break
        else:
            pytest.fail("Death of an unexpected process.")

    cemetary.add("adameve")


def test_dashboard_process_lifecycle():
    sim = Simulator()
    cemetary = set()
    Endpoint().with_proc_in(sim, 0, adameve, cemetary)
    sim.run()
    assert cemetary == {"adameve", "cain", "abel", "seth"}
