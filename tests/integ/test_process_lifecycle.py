import sys
from typing import Set, Mapping

import pytest

from itsim.software.context import Context
from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management.process import Process
from itsim.simulator import Simulator, advance, now
from itsim.types import Timeout


Cemetary = Set[str]
Name2Child = Mapping[str, Process]


class Character:

    def __init__(self, name, year_born, year_dead):
        super().__init__()
        self._name = name
        self._year_born = year_born
        self._year_dead = year_dead

    @property
    def year_born(self):
        return self._year_born

    @property
    def year_dead(self):
        return self._year_dead

    @property
    def lifetime(self):
        return self._year_dead - self._year_born

    @property
    def name(self):
        return self._name

    def life(self, context: Context, cemetary: Cemetary, child: Name2Child) -> None:
        try:
            assert context.process is child[self.name]
            self._live(context, child)
        finally:
            cemetary.add(self.name)


class Cain(Character):

    def __init__(self):
        super().__init__("Cain", 0, 730)

    def _live(self, context: Context, child: Name2Child) -> None:
        advance(Abel.YEAR_DEAD - now())
        child["Abel"].kill()
        advance(self.year_dead - now())


class Abel(Character):

    YEAR_DEAD = 130

    def __init__(self):
        super().__init__("Abel", 0, Abel.YEAR_DEAD)

    def _live(self, context: Context, child: Name2Child) -> None:
        advance(1000)  # Dude wants to live forever but...


class Seth(Character):

    def __init__(self):
        super().__init__("Seth", Abel.YEAR_DEAD, Abel.YEAR_DEAD + 912)

    def _live(self, context: Context, child: Name2Child) -> None:
        advance(self.lifetime)


class Humanity(Character):

    def __init__(self):
        super().__init__("Humanity", 0, sys.maxsize)

    def _live(self, context: Context, child: Name2Child) -> None:
        advance(100000)  # Will not end.


def adameve(context: Context, cemetary: Cemetary) -> None:
    child: Name2Child = {}
    for c in [Cain(), Abel(), Seth(), Humanity()]:
        child[c.name] = context.process.fork_exec_in(c.year_born, c.life, cemetary, child)

    for c in [Abel(), Cain(), Seth()]:
        child[c.name].wait()
        assert now() == pytest.approx(c.year_dead)

    try:
        child["Humanity"].wait(2000)
        pytest.fail("Humanity has yet to start killing itself with CO2.")
    except Timeout:
        pass

    cemetary.add("adameve")


def test_context_process_lifecycle():
    sim = Simulator()
    cemetary = set()
    Endpoint().with_proc(sim, adameve, cemetary)
    sim.run(4000)
    assert cemetary == {"adameve", "Cain", "Abel", "Seth"}
