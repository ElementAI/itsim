from typing import Set, Mapping

import pytest

from itsim.software.context import Context
from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management.process import Process
from itsim.simulator import Simulator, advance
from itsim.types import Timeout


Cemetary = Set[str]
Name2Child = Mapping[str, Process]


def cain(d: Context, cemetary: Cemetary, child: Name2Child) -> None:
    advance(130)
    assert d.process is child["cain"]
    child["abel"].kill()
    advance(730 - 130)
    cemetary.add("cain")


def abel(d: Context, cemetary: Cemetary, child: Name2Child) -> None:
    assert d.process is child["abel"]
    try:
        advance(1000)
    finally:
        cemetary.add("abel")


def seth(d: Context, cemetary: Cemetary, child: Name2Child) -> None:
    assert d.process is child["seth"]
    advance(912)
    cemetary.add("seth")


def humanity(d: Context, *_) -> None:
    advance(100000)  # Will not end.


def adameve(d: Context, cemetary: Cemetary) -> None:
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


def test_context_process_lifecycle():
    sim = Simulator()
    cemetary = set()
    Endpoint().with_proc(sim, adameve, cemetary)
    sim.run(4000)
    assert cemetary == {"adameve", "cain", "abel", "seth"}
