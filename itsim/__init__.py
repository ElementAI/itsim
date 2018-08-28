from abc import ABC, abstractmethod, abstractproperty
from typing import Iterable

from itsim.it_objects.packet import Packet
from itsim.types import Address


class _Node(ABC):

    @abstractproperty
    def addresses(self) -> Iterable[Address]:
        raise NotImplementedError("Meant to be implemented by class itsim.node.Node.")
        return []

    @abstractmethod
    def _send_to_network(self, packet: Packet) -> None:
        raise NotImplementedError("Meant to be implemented by class itsim.node.Node.")
