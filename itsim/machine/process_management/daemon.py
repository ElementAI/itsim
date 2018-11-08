from typing import Optional

from itsim import ITObject
from itsim.simulator import Simulator
from itsim.types import PortsRepr


class Daemon(ITObject):
    """
    Base class for application services provided by Internet nodes.

    :param tcp: Set of TCP ports on which this daemon listens.
    :param udp: Set of UDP ports on which this daemon listens.
    """

    def __init__(self, sim: Simulator, tcp: Optional[PortsRepr] = None, udp: Optional[PortsRepr] = None) -> None:
        raise NotImplementedError()


class Service(ITObject):
    """
    Description of a service implemented over a network.
    """
    pass
