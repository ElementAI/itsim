from abc import abstractmethod
from typing import Optional, cast

from itsim import AbstractITObject
from itsim.network.packet import Packet
from itsim.types import Address, as_cidr, Cidr, CidrRepr, AddressRepr, as_address


class Forwarding(AbstractITObject):
    """
    Rule indicating where a packet is to be transferred when its destination belongs to the CIDR associated to this
    object.
    """

    def __init__(self, cr: Optional[CidrRepr] = None) -> None:
        super().__init__()
        self._cidr = as_cidr(cr or "0.0.0.0/0")

    @property
    def cidr(self) -> Cidr:
        """
        CIDR targeted by this forwarding rule.
        """
        return self._cidr

    @abstractmethod
    def get_hop(self, dest: Address) -> Address:
        pass

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self.cidr == other.cidr


class Local(Forwarding):
    """
    Local forwarding: packet is delivered directly to its destination.
    """

    def get_hop(self, dest: Address) -> Address:
        return dest


class Relay(Forwarding):
    """
    Packet relay through a gateway.
    """

    def __init__(self, gr: AddressRepr, cr: Optional[CidrRepr] = None) -> None:
        super().__init__(cr)
        self._gateway = as_address(gr)

    def get_hop(self, dest: Address) -> Address:
        return self._gateway

    def __eq__(self, other: object) -> bool:
        if not Forwarding.__eq__(self, other):
            return False
        return self._gateway == cast(Relay, other)._gateway
