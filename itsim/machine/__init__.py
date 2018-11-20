from abc import abstractproperty, abstractmethod
from typing import Optional, Iterator

from itsim.__init__ import AbstractITObject
from itsim.network.location import LocationRepr
from itsim.network.packet import Packet
from itsim.types import Payload, Address, PortRepr


class _Socket(AbstractITObject):

    @abstractmethod
    def __enter__(self) -> "_Socket":
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractproperty
    def is_closed(self) -> bool:
        pass

    def send(self, dr: LocationRepr, size: int, payload: Optional[Payload] = None) -> None:
        pass

    def recv(self, timeout: Optional[float] = None) -> Packet:
        pass


class _Node(AbstractITObject):

    @abstractmethod
    def addresses(self) -> Iterator[Address]:
        pass

    @abstractmethod
    def bind(self, pr: PortRepr = None) -> _Socket:
        pass
