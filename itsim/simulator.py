from typing import Optional
from uuid import UUID

import greensim
from itsim.types import Timeout


class Simulator(greensim.Simulator):

    # Todo: validate this in unit tests.
    @property
    def uuid(self) -> UUID:
        return UUID(self._name)

    def uuid_str(self) -> str:
        return str(self.uuid)


class _Process(greensim.Process):
    pass


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
