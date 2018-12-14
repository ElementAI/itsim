from typing import Set, Mapping

import pytest

from itsim.machine.dashboard import Dashboard
from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management.process import Process
from itsim.simulator import Simulator, advance
from itsim.types import Timeout


Cemetary = Set[str]
Name2Child = Mapping[str, Process]


def cain(d: Dashboard, cemetary: Cemetary, child: Name2Child) -> None:
    advance(130)
    assert d.process is child["cain"]
    child["abel"].kill()
    advance(730 - 130)
    cemetary.add("cain")


def abel(d: Dashboard, cemetary: Cemetary, child: Name2Child) -> None:
    assert d.process is child["abel"]
    try:
        advance(1000)
    finally:
        cemetary.add("abel")


def seth(d: Dashboard, cemetary: Cemetary, child: Name2Child) -> None:
    assert d.process is child["seth"]
    advance(912)
    cemetary.add("seth")


def humanity(d: Dashboard, *_) -> None:
    advance(100000)  # Will not end.


def adameve(d: Dashboard, cemetary: Cemetary) -> None:
    child: Name2Child = {}
    for name, moment in [(cain, 0), (abel, 0), (seth, 130), (humanity, 0)]:
        child[name.__name__] = d.run_proc_in(moment, name, cemetary, child)

    for name_expected, moment in [("abel", 130), ("cain", 730), ("seth", 130 + 912)]:
        child[name_expected].wait()
        assert d.now() == pytest.approx(moment)

    try:
        child["humanity"].wait(2000)
        pytest.fail("Humanity has yet to start killing itself with CO2.")
    except Timeout:
        pass

    cemetary.add("adameve")


def test_dashboard_process_lifecycle():
    sim = Simulator()
    cemetary = set()
    Endpoint().with_proc(sim, adameve, cemetary)
    sim.run(4000)
    assert cemetary == {"adameve", "cain", "abel", "seth"}
