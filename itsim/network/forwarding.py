from abc import ABC, abstractmethod
from typing import Optional, cast

from itsim.network.packet import Packet
from itsim.types import Address, as_cidr, Cidr, CidrRepr, AddressRepr, as_address


class Forwarding(ABC):

    def __init__(self, cr: Optional[CidrRepr] = None) -> None:
        super().__init__()
        self._cidr = as_cidr(cr or "0.0.0.0/0")

    @property
    def cidr(self) -> Cidr:
        return self._cidr

    @abstractmethod
    def get_hop(self, packet: Packet) -> Address:
        pass

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self.cidr == other.cidr


class Local(Forwarding):

    def get_hop(self, packet: Packet) -> Address:
        return packet.dest.hostname_as_address()


class Relay(Forwarding):

    def __init__(self, gr: AddressRepr, cr: Optional[CidrRepr] = None) -> None:
        super().__init__(cr)
        self._gateway = as_address(gr)

    def get_hop(self, packet: Packet) -> Address:
        return self._gateway

    def __eq__(self, other: object) -> bool:
        if not Forwarding.__eq__(self, other):
            return False
        return self._gateway == cast(Relay, other)._gateway
