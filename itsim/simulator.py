from typing import Optional, Any, Callable, List
from uuid import UUID

import greensim
from itsim import ITObject, Tag
from itsim.types import Timeout


class Simulator(greensim.Simulator):

    # Todo: validate this in unit tests.
    @property
    def uuid(self) -> UUID:
        return UUID(self._name)

    def uuid_str(self) -> str:
        return str(self.uuid)


def get_tags(tag_bearer: Optional[Callable] = None) -> List[Tag]:
    if tag_bearer is None:
        return list(greensim.Process.current().iter_tags())
    elif hasattr(tag_bearer, greensim.GREENSIM_TAG_ATTRIBUTE):
        return list(getattr(tag_bearer, greensim.GREENSIM_TAG_ATTRIBUTE))
    return []


class SimulatedComputation(ITObject):

    def __init__(self, *tags: Tag) -> None:
        super().__init__(*tags)
        self._gp: Optional[greensim.Process] = None

    @property
    def gp(self) -> greensim.Process:
        if self._gp is None:
            raise RuntimeError("Must set the greensim process before accessing it.")
        return self._gp

    @gp.setter
    def gp(self, v: greensim.Process) -> None:
        self._gp = v
        self._gp.tag_with(*list(self.iter_tags()))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SimulatedComputation):
            return self.uuid == other.uuid
        return False

    def __hash__(self) -> int:
        return hash(self.uuid)


class Interrupt(greensim.Interrupt):
    pass


class Event:
    """
    Models an unrealized event in the simulation, which can then be fired to enact its realization.
    """

    def __init__(self):
        super().__init__()
        self._signal = greensim.Signal().turn_off()

    def fire(self) -> None:
        """
        Enacts the realization of the event, resuming all processes :py:meth:`wait` ing on it.
        """
        self._signal.turn_on()

    def has_fired(self) -> bool:
        """
        Tells whether the signal has fired or not.
        """
        return self._signal.is_on

    def wait(self, timeout: Optional[float] = None) -> None:
        """
        Waits for the event to be :py:meth:`fire` d, until the given timeout has elapsed (in simulated time).
        """
        try:
            self._signal.wait(timeout)
        except greensim.Timeout:
            raise Timeout()


add = greensim.add
add_in = greensim.add_in
advance = greensim.advance
now = greensim.now
