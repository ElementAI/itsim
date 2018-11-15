from abc import abstractmethod, abstractproperty

from typing import Iterable, Callable

from itsim import AbstractITObject
from itsim.simulator import Simulator
from itsim.types import Address, PortRepr, Protocol


class _Node(AbstractITObject):

    @abstractproperty
    def addresses(self) -> Iterable[Address]:
        raise NotImplementedError("Meant to be implemented by class itsim.machine.Node.")
        return []

    @abstractmethod
    def networking_daemon(self, sim: Simulator, protocol: Protocol, *ports: PortRepr) -> Callable:
        raise NotImplementedError("Meant to be implemented by class itsim.machine.Node.")
        return lambda: 0
