from typing import Set, Mapping

import pytest

from itsim.machine.api import API
from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management.process import Process
from itsim.simulator import Simulator, advance


Cemetary = Set[str]
Name2Child = Mapping[str, Process]


def cain(api: API, cemetary: Cemetary, child: Name2Child):
    advance(130)
    assert api.current_process == child["cain"]
    child["abel"].kill()
    advance(730 - 130)
    cemetary.add("cain")


def abel(api: API, cemetary: Cemetary, child: Name2Child):
    assert api.current_process == child["abel"]
    try:
        advance(1000)
    finally:
        cemetary.add("abel")


def seth(api: API, cemetary: Cemetary, child: Name2Child):
    assert api.current_process == child["seth"]
    advance(912)
    cemetary.add("seth")


def adameve(api: API, cemetary: Cemetary):
    child: Name2Child = {}
    for name, moment in [(cain, 0), (abel, 0), (seth, 122)]:
        child[name] = api.run_proc_in(moment, name, cemetary, child)

    for name_expected, moment in [("abel", 130), ("cain", 730), ("seth", 130 + 912)]:
        proc_dead = api.wait_proc()
        assert api.now() == pytest.approx(moment)
        for name, proc in child.items():
            if proc.pid == proc_dead.pid:
                assert name == name_expected
                break
        else:
            pytest.fail("Death of an unexpected process.")

    cemetary.add("adameve")


def test_api_process_lifecycle():
    sim = Simulator()
    cemetary = set()
    Endpoint().with_proc_in(sim, 0, adameve, cemetary)
    sim.run()
    assert cemetary == {"adameve", "cain", "abel", "seth"}
